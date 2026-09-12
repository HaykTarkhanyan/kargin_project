"""Add an empty `collections` column to kargin_eng.csv.

Membership in a site collection ("they play cards", "they watch TV"), as one or
more `;`-separated ascii slugs defined in data/collections.csv. See
docs/superpowers/specs/2026-09-12-collections-design.md and DECISIONS.md.

Blank is the normal state: most sketches belong to no collection. Unlike
add_status_final.py there is nothing to back-fill, so this only ever adds the
column and never touches a row that already has a value.

The column MUST exist before any correction can be applied to it -- the review
store refuses a correction naming a column the CSV does not have.

Backs up kargin_eng.csv first and verifies every pre-existing column is unchanged
afterwards, refusing to save if anything else moved.

Usage:
    uv run python scripts/add_collections_column.py            # dry run
    uv run python scripts/add_collections_column.py --write
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from kargin_review.store import backup

COLUMN = "collections"

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "add_collections_column.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)


def main(source: Path, backups_dir: Path, write: bool) -> int:
    if not source.exists():
        logging.error(f"not found: {source}")
        return 2

    before = pd.read_csv(source, dtype=str, keep_default_na=False)
    if COLUMN in before.columns:
        filled = (before[COLUMN].str.strip() != "").sum()
        logging.info(f"{COLUMN} already present on {len(before)} rows; {filled} carry a value")
        return 0

    after = before.copy()
    after[COLUMN] = ""
    logging.info(f"adding empty {COLUMN} to all {len(after)} rows")

    for col in before.columns:
        if not before[col].equals(after[col]):
            logging.error(f"refusing to write: pre-existing column {col!r} changed")
            return 1
    logging.info(f"verified {len(before.columns)} pre-existing column(s) unchanged")

    if not write:
        logging.info("dry run - nothing written. Re-run with --write.")
        return 0

    saved = backup(source, backups_dir)
    logging.info(f"backed up {source} -> {saved}")
    tmp = source.with_name(source.name + ".tmp")
    # CRLF matches the file on disk; quoted fields contain embedded newlines.
    after.to_csv(tmp, index=False, encoding="utf-8", lineterminator="\r\n")
    tmp.replace(source)
    logging.info(f"wrote {source} with {len(after.columns)} columns")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", default=Path("kargin_eng.csv"), type=Path)
    p.add_argument("--backups", default=Path("data/backups"), type=Path)
    p.add_argument("--write", action="store_true", help="actually save")
    a = p.parse_args()
    sys.exit(main(a.source, a.backups, a.write))
