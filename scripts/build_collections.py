"""Build web/public/data/collections.json from the CSVs.

Membership comes from the `collections` column of kargin_eng.csv, the Armenian
names and descriptions from data/collections.csv. Separate from
build_site_data.py on purpose: collections need neither the YouTube metadata nor
the songs, transcripts or visual annotations that build feeds on.

Usage:
    PYTHONPATH=scripts uv run python scripts/build_collections.py
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

from kargin_build.collections import build_collections

ROOT = Path(__file__).resolve().parents[1]

LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "build_collections.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)


def main(source: Path, definitions: Path, out: Path) -> int:
    for path in (source, definitions):
        if not path.exists():
            logging.error(f"not found: {path}")
            return 2

    rows = pd.read_csv(source, dtype=str, keep_default_na=False).to_dict("records")
    defs = pd.read_csv(definitions, dtype=str, keep_default_na=False).to_dict("records")

    collections = build_collections(rows, defs)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(collections, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")

    total = sum(len(c["sketchIds"]) for c in collections)
    for c in collections:
        logging.info(f"{c['slug']:>16}: {len(c['sketchIds']):>3} sketch(es)  {c['name']}")
    logging.info(f"wrote {len(collections)} collection(s), {total} membership(s) -> {out}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", default=ROOT / "kargin_eng.csv", type=Path)
    p.add_argument("--definitions", default=ROOT / "data" / "collections.csv", type=Path)
    p.add_argument("--out", default=ROOT / "web" / "public" / "data" / "collections.json", type=Path)
    a = p.parse_args()
    raise SystemExit(main(a.source, a.definitions, a.out))
