"""Turn ticked collection candidates into rows for data/corrections.csv.

Reads data/collections_candidates.csv, takes every row whose `include` starts with
y, groups the themes per sketch into one `;`-joined value, and appends a correction
per sketch. The existing apply_corrections.py then writes them into
kargin_eng.csv with its own backup and validation:

    uv run python scripts/non_essential/apply_collection_candidates.py --write
    uv run python scripts/apply_corrections.py --write

Going through corrections.csv rather than writing the CSV directly means
collection edits get the same backup, the same old_value check and the same audit
trail as any other curation change. A correction is only emitted when the value
would actually change, so re-running is a no-op.

`old_value` is whatever the sketch has today, because the review store refuses a
correction whose old_value no longer matches the source.

Usage:
    uv run python scripts/non_essential/apply_collection_candidates.py            # dry run
    uv run python scripts/non_essential/apply_collection_candidates.py --write
"""
from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
COLUMN = "collections"
CORRECTION_COLUMNS = ["video_id", "field", "old_value", "new_value", "edited_at"]

LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "apply_collection_candidates.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)


def slugs_per_sketch(candidates: pd.DataFrame) -> dict[str, str]:
    """{video_id: "cards;tv"} from the rows marked include=y."""
    ticked = candidates[candidates["include"].str.strip().str.lower().str.startswith("y")]
    out: dict[str, list[str]] = {}
    for row in ticked.to_dict("records"):
        out.setdefault(row["video_id"], []).append(row["theme"].strip())
    return {vid: ";".join(sorted(set(themes))) for vid, themes in out.items()}


def main(candidates_path: Path, source: Path, corrections: Path, write: bool) -> int:
    if not candidates_path.exists():
        logging.error(f"not found: {candidates_path}. Run seed_collection_candidates.py first.")
        return 2

    candidates = pd.read_csv(candidates_path, dtype=str, keep_default_na=False)
    wanted = slugs_per_sketch(candidates)
    if not wanted:
        logging.error("no rows marked include=y; nothing to apply")
        return 1
    logging.info(f"{len(wanted)} sketch(es) marked across "
                 f"{candidates['theme'].nunique()} theme(s)")

    src = pd.read_csv(source, dtype=str, keep_default_na=False)
    if COLUMN not in src.columns:
        logging.error(f"{source.name} has no {COLUMN!r} column; "
                      "run scripts/add_collections_column.py --write first")
        return 1
    current = {r["video_id"]: (r.get(COLUMN) or "").strip() for r in src.to_dict("records")}

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows, unchanged, missing = [], 0, []
    for vid, value in sorted(wanted.items()):
        if vid not in current:
            missing.append(vid)
            continue
        if current[vid] == value:
            unchanged += 1
            continue
        rows.append({"video_id": vid, "field": COLUMN, "old_value": current[vid],
                     "new_value": value, "edited_at": now})

    if missing:
        logging.error(f"{len(missing)} ticked video_id(s) are not in {source.name}: "
                      f"{', '.join(missing[:5])}")
        return 1
    logging.info(f"{len(rows)} correction(s) to write, {unchanged} already correct")
    for r in rows[:10]:
        logging.info(f"  {r['video_id']}: {r['old_value']!r} -> {r['new_value']!r}")
    if len(rows) > 10:
        logging.info(f"  ... and {len(rows) - 10} more")

    if not rows:
        logging.info("nothing to do")
        return 0
    if not write:
        logging.info("dry run - nothing written. Re-run with --write, "
                     "then apply with scripts/apply_corrections.py --write")
        return 0

    existing = (pd.read_csv(corrections, dtype=str, keep_default_na=False)
                if corrections.exists() else pd.DataFrame(columns=CORRECTION_COLUMNS))
    combined = pd.concat([existing, pd.DataFrame(rows, columns=CORRECTION_COLUMNS)],
                         ignore_index=True)
    combined.to_csv(corrections, index=False, encoding="utf-8", lineterminator="\r\n")
    logging.info(f"appended {len(rows)} row(s) to {corrections} "
                 f"({len(existing)} were already there)")
    logging.info("now run: uv run python scripts/apply_corrections.py --write")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidates", default=ROOT / "data" / "collections_candidates.csv", type=Path)
    p.add_argument("--source", default=ROOT / "kargin_eng.csv", type=Path)
    p.add_argument("--corrections", default=ROOT / "data" / "corrections.csv", type=Path)
    p.add_argument("--write", action="store_true", help="actually append to corrections.csv")
    a = p.parse_args()
    raise SystemExit(main(a.candidates, a.source, a.corrections, a.write))
