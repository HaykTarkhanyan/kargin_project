"""Storage for manual curation edits. Never writes kargin_eng.csv.

The review UI records corrections into a separate overlay file so the curated
source cannot be damaged by a bug in the editor. Applying them to
kargin_eng.csv is a deliberate, separate step (scripts/apply_corrections.py).

Overlay shape -- one row per changed field, not one row per video:

    video_id, field, old_value, new_value, edited_at

`old_value` is what kargin_eng.csv held when the field was FIRST edited, and it
is never rewritten by later edits to the same field. That makes it a guard:
apply refuses any correction whose old_value no longer matches the source, so
if the CSV changed underneath (a rebuild, a hand edit, a git operation) the
correction is reported as stale instead of silently clobbering newer data.

Writes are atomic (temp file + os.replace) and the previous overlay is copied
into data/backups/ first, so no save can leave a half-written file or destroy
the prior state.
"""
from __future__ import annotations

import os
import shutil
import threading
from datetime import datetime
from pathlib import Path

import pandas as pd

# Fields the UI is allowed to touch. Anything else -- id, links, video_id,
# duplicate_of -- is a key or derived, and an edit to it would desynchronise the
# CSV from the audio files, the site payload and the duplicate report.
EDITABLE_FIELDS = (
    "titles",
    "text",
    "text_common",
    "main_actors",
    "main_actors_count",
    "roles_names",
    "location",
    "lighting",
    "languages",
    "done",
)

COLUMNS = ["video_id", "field", "old_value", "new_value", "edited_at"]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def clean(v) -> str:
    """CSV cell -> plain string. NaN and the literal 'nan' both become ''."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    s = str(v)
    return "" if s == "nan" else s


def backup(path: Path, backups_dir: Path) -> Path | None:
    """Timestamped copy of `path` before it is overwritten. None if absent.

    Never prunes: deleting backups is the one operation that could lose data,
    and these files are a few KB each.
    """
    if not path.exists():
        return None
    backups_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    dest = backups_dir / f"{path.stem}_{stamp}{path.suffix}"
    shutil.copy2(path, dest)
    return dest


def write_atomic(df: pd.DataFrame, path: Path) -> None:
    """Write via a temp file then replace, so a crash cannot truncate the target."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    df.to_csv(tmp, index=False, encoding="utf-8", lineterminator="\n")
    os.replace(tmp, path)


def load(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path} missing columns: {missing}")  # loud, not silently rebuilt
    return df[COLUMNS]


def as_map(df: pd.DataFrame) -> dict[tuple[str, str], dict]:
    return {(r["video_id"], r["field"]): r for r in df.to_dict("records")}


# Every mutation is read-modify-write on one small file. Flask's dev server is
# threaded by default, so two saves in flight (a double-click, two tabs) could
# each read the same overlay and the second write would silently drop the first.
_WRITE_LOCK = threading.Lock()


def record_many(path: Path, backups_dir: Path, video_id: str,
                updates: dict[str, tuple[str, str]]) -> dict[str, str]:
    """Apply several field edits as ONE load/backup/write.

    `updates` maps field -> (source_value, new_value). Returns field -> status,
    one of created / updated / reverted / unchanged.

    Batched rather than looping `record`: saving five fields would otherwise mean
    five rewrites and five backup files for a single user action.

    `source_value` is what kargin_eng.csv holds now, and is used only when the
    field has no correction yet -- re-editing keeps the ORIGINAL old_value so the
    staleness guard in `plan` still compares against the real source.

    Setting a field back to its source value deletes the correction rather than
    storing a no-op, keeping the overlay a true list of pending changes.
    """
    bad = [f for f in updates if f not in EDITABLE_FIELDS]
    if bad:
        raise ValueError(f"field not editable: {bad!r}")   # loud fail, never silently ignored
    if not updates:
        return {}

    with _WRITE_LOCK:
        df = load(path)
        status: dict[str, str] = {}
        drop = pd.Series(False, index=df.index)
        new_rows = []

        for field, (source_value, new_value) in updates.items():
            key_mask = (df["video_id"] == video_id) & (df["field"] == field)
            existing = df[key_mask]
            original = existing.iloc[0]["old_value"] if len(existing) else clean(source_value)

            if clean(new_value) == clean(original):
                status[field] = "reverted" if len(existing) else "unchanged"
                drop |= key_mask
                continue

            status[field] = "updated" if len(existing) else "created"
            drop |= key_mask
            new_rows.append({
                "video_id": video_id, "field": field,
                "old_value": original, "new_value": clean(new_value),
                "edited_at": _now(),
            })

        if all(s == "unchanged" for s in status.values()):
            return status                                   # nothing to write at all

        kept = df[~drop]
        out = pd.concat([kept, pd.DataFrame(new_rows)], ignore_index=True) if new_rows else kept
        backup(path, backups_dir)
        write_atomic(out[COLUMNS], path)
        return status


def record(path: Path, backups_dir: Path, video_id: str, field: str,
           source_value: str, new_value: str) -> dict:
    """Single-field convenience wrapper around `record_many`."""
    status = record_many(path, backups_dir, video_id, {field: (source_value, new_value)})[field]
    return {"status": status}


def plan(source_csv: Path, corrections_path: Path) -> dict:
    """What applying the overlay would do, without touching anything.

    Splits into `apply` (source still matches old_value) and `stale` (it does
    not -- the source moved since the edit, so applying would discard whatever
    changed it).
    """
    src = pd.read_csv(source_csv, dtype=str, keep_default_na=False)
    if "video_id" not in src.columns:
        raise ValueError(f"{source_csv} has no video_id column")
    by_vid = {r["video_id"]: r for r in src.to_dict("records")}

    to_apply, stale, unknown = [], [], []
    for r in load(corrections_path).to_dict("records"):
        row = by_vid.get(r["video_id"])
        if r["field"] not in src.columns:
            # Applying would silently ADD a column to the source CSV.
            unknown.append({**r, "reason": f"no such column: {r['field']}"})
        elif row is None:
            unknown.append({**r, "reason": "video_id not in source"})
        elif clean(row.get(r["field"])) != clean(r["old_value"]):
            stale.append({**r, "current_value": clean(row.get(r["field"]))})
        else:
            to_apply.append(r)
    return {"apply": to_apply, "stale": stale, "unknown": unknown}
