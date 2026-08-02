"""Add a `status_final` column to kargin_eng.csv, defaulting to "false".

Marks whether a row's curation has been reviewed and signed off. Separate from
the existing `done`: that came from the original curation pass, this one tracks
the review happening now.

Idempotent -- re-running leaves existing values alone and only fills rows that
lack one, so it is safe after the review UI has already flipped some to "true".

Backs up kargin_eng.csv before writing and verifies every pre-existing column is
byte-identical afterwards, refusing to save if anything else moved.

Usage:
    uv run python scripts/add_status_final.py            # dry run
    uv run python scripts/add_status_final.py --write
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from kargin_review.store import backup

COLUMN = "status_final"
DEFAULT = "false"

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "add_status_final.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)


def main(source: Path, backups_dir: Path, write: bool) -> int:
    if not source.exists():
        logging.error(f"not found: {source}")
        return 2

    before = pd.read_csv(source, dtype=str, keep_default_na=False)
    after = before.copy()

    if COLUMN in after.columns:
        blank = (after[COLUMN].str.strip() == "").sum()
        logging.info(f"{COLUMN} already present; {blank} blank row(s) to fill")
        after.loc[after[COLUMN].str.strip() == "", COLUMN] = DEFAULT
    else:
        logging.info(f"adding {COLUMN} = {DEFAULT!r} to all {len(after)} rows")
        after[COLUMN] = DEFAULT

    if after.equals(before):
        logging.info("nothing to change")
        return 0

    # Every column that existed before must be untouched; only the new one moves.
    for col in before.columns:
        if not before[col].equals(after[col]):
            logging.error(f"refusing to write: pre-existing column {col!r} changed")
            return 1
    logging.info(f"verified {len(before.columns)} pre-existing column(s) unchanged")
    logging.info(f"distribution: {after[COLUMN].value_counts().to_dict()}")

    if not write:
        logging.info("dry run — nothing written. Re-run with --write.")
        return 0

    saved = backup(source, backups_dir)
    logging.info(f"backed up {source} -> {saved}")
    tmp = source.with_name(source.name + ".tmp")
    # CRLF matches the file on disk; 114 quoted fields contain embedded newlines.
    after.to_csv(tmp, index=False, encoding="utf-8", lineterminator="\r\n")
    tmp.replace(source)
    logging.info(f"wrote {source} with {len(after.columns)} columns")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", default=Path("kargin_eng.csv"), type=Path)
    p.add_argument("--backups", default=Path("data/backups"), type=Path)
    p.add_argument("--write", action="store_true")
    a = p.parse_args()
    sys.exit(main(a.source, a.backups, a.write))
