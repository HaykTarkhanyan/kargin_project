"""Merge data/corrections.csv into kargin_eng.csv. The ONLY writer of that file.

Dry-run by default: prints exactly what would change and exits without touching
anything. Pass --write to apply, which first copies kargin_eng.csv into
data/backups/.

Refuses any correction whose recorded old_value no longer matches the source.
That means the CSV moved since the edit was made -- a rebuild, a hand edit, a
branch switch -- and applying would silently discard whatever changed it. Those
are reported as STALE and skipped; re-open them in the review UI to redo the edit
against current data.

Usage:
    uv run python scripts/apply_corrections.py            # dry run
    uv run python scripts/apply_corrections.py --write
    uv run python scripts/apply_corrections.py --write --clear   # also empty the overlay
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from kargin_review.store import COLUMNS, backup, clean, load, plan, write_atomic

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "apply_corrections.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)


def preview(value: str, width: int = 70) -> str:
    one_line = " ".join(str(value).split())
    return one_line[:width] + ("…" if len(one_line) > width else "")


def main(source_csv: Path, corrections: Path, backups_dir: Path,
         write: bool, clear: bool) -> int:
    if not corrections.exists():
        logging.info(f"no corrections file at {corrections} — nothing to do")
        return 0

    p = plan(source_csv, corrections)
    logging.info(
        f"{len(p['apply'])} to apply, {len(p['stale'])} stale, {len(p['unknown'])} unknown video_id"
    )

    for r in p["apply"]:
        logging.info(f"  {r['video_id']} .{r['field']}")
        logging.info(f"      - {preview(r['old_value'])}")
        logging.info(f"      + {preview(r['new_value'])}")
    for r in p["stale"]:
        logging.warning(
            f"  STALE {r['video_id']} .{r['field']} — source changed since the edit"
        )
        logging.warning(f"      recorded old: {preview(r['old_value'])}")
        logging.warning(f"      source now:   {preview(r['current_value'])}")
    for r in p["unknown"]:
        logging.error(f"  UNKNOWN video_id {r['video_id']} (.{r['field']}) — not in {source_csv.name}")

    if not write:
        logging.info("dry run — nothing written. Re-run with --write to apply.")
        return 0
    if not p["apply"]:
        logging.info("nothing applicable to write")
        return 0

    df = pd.read_csv(source_csv, dtype=str, keep_default_na=False)
    idx = {vid: i for i, vid in enumerate(df["video_id"])}
    for r in p["apply"]:
        df.at[idx[r["video_id"]], r["field"]] = r["new_value"]

    saved = backup(source_csv, backups_dir)
    logging.info(f"backed up {source_csv} -> {saved}")
    # CRLF matches how kargin_eng.csv already sits on disk (114 quoted fields
    # contain embedded newlines, so this is not cosmetic).
    tmp = source_csv.with_name(source_csv.name + ".tmp")
    df.to_csv(tmp, index=False, encoding="utf-8", lineterminator="\r\n")
    tmp.replace(source_csv)
    logging.info(f"applied {len(p['apply'])} correction(s) to {source_csv}")

    if clear:
        remaining = [r for r in load(corrections).to_dict("records")
                     if (r["video_id"], r["field"]) not in
                     {(a["video_id"], a["field"]) for a in p["apply"]}]
        backup(corrections, backups_dir)
        write_atomic(pd.DataFrame(remaining, columns=COLUMNS), corrections)
        logging.info(f"cleared applied rows from {corrections}; {len(remaining)} left")

    return 1 if p["stale"] or p["unknown"] else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", default=Path("kargin_eng.csv"), type=Path)
    p.add_argument("--corrections", default=Path("data/corrections.csv"), type=Path)
    p.add_argument("--backups", default=Path("data/backups"), type=Path)
    p.add_argument("--write", action="store_true", help="actually modify kargin_eng.csv")
    p.add_argument("--clear", action="store_true", help="with --write, drop applied rows from the overlay")
    a = p.parse_args()
    sys.exit(main(a.source, a.corrections, a.backups, a.write, a.clear))
