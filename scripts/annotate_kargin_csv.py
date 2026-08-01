"""Add `id`, `video_id` and `duplicate_of` columns to kargin_eng.csv.

  id            zero-padded 3-digit sequence, e.g. "042". This is the 1-based row
                number in data/youtube_metadata.csv, which is exactly the NNN_
                prefix download_audio.py gave the audio files -- so row "042"
                pairs with data/audio/042_<title>_<video_id>.webm. Read it back
                with dtype={"id": str} or pandas eats the leading zeros.
  video_id      the 11-char YouTube id, previously re-derived from `links` on
                every run of every script that needed it.
  duplicate_of  URLs of the other uploads of this same recording, ';'-separated
                (matching the separator the `text` column already uses). Empty
                for the ~99% of rows with no duplicate.

`duplicate_of` is symmetric: every member of a duplicate group lists all the
others, so no information depends on which row you happen to be looking at.
Which upload is the "real" one is a different question and lives in
data/duplicates.csv (`canonical` column = most-viewed of the group).

Duplicates come from data/duplicates.csv (audio fingerprint matches), so run
fingerprint_audio.py then detect_duplicates.py first. Only rows with
verdict="duplicate" are used; "candidate" rows are left out pending review.

Idempotent: re-running overwrites the three columns rather than appending.
Writes CRLF + UTF-8 to match the existing file.

Usage:
    uv run python scripts/annotate_kargin_csv.py
    uv run python scripts/annotate_kargin_csv.py --dry-run
    uv run python scripts/annotate_kargin_csv.py --include-candidates
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

import pandas as pd

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "annotate_kargin_csv.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

VIDEO_ID_FROM_URL = re.compile(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})")
NEW_COLUMNS = ("id", "video_id", "duplicate_of")
DUP_SEPARATOR = "; "


def duplicate_groups(dup_path: Path, include_candidates: bool) -> list[set[str]]:
    """Merge duplicate pairs into groups of video_ids."""
    if not dup_path.exists():
        raise FileNotFoundError(f"{dup_path} not found -- run scripts/detect_duplicates.py first")
    d = pd.read_csv(dup_path)
    if not include_candidates:
        d = d[d["verdict"] == "duplicate"]

    groups: list[set[str]] = []
    for a, b in zip(d["video_id_a"], d["video_id_b"]):
        touching = [g for g in groups if a in g or b in g]
        merged = {a, b}.union(*touching) if touching else {a, b}
        groups = [g for g in groups if g not in touching]
        groups.append(merged)
    return groups


def main(csv_path: Path, metadata_path: Path, dup_path: Path,
         include_candidates: bool, dry_run: bool) -> int:
    k = pd.read_csv(csv_path)
    original_cols = [c for c in k.columns if c not in NEW_COLUMNS]
    logging.info(f"{len(k)} rows, {len(original_cols)} existing columns")

    k["video_id"] = k["links"].map(
        lambda u: m.group(1) if isinstance(u, str) and (m := VIDEO_ID_FROM_URL.search(u)) else None
    )
    if k["video_id"].isna().any():
        bad = k.loc[k["video_id"].isna(), "links"].tolist()
        raise ValueError(f"{len(bad)} row(s) have no parseable video_id: {bad[:5]}")
    if k["video_id"].duplicated().any():
        # Not a content duplicate -- this would mean the same URL is listed twice,
        # which would break `id` uniqueness and the site's per-video routing.
        dupes = k.loc[k["video_id"].duplicated(), "video_id"].tolist()
        raise ValueError(f"the same video_id appears on multiple rows: {dupes}")

    # id == position in youtube_metadata.csv == the audio filename's NNN_ prefix.
    meta_ids = pd.read_csv(metadata_path)["video_id"].tolist()
    seq_of = {vid: i for i, vid in enumerate(meta_ids, 1)}
    unknown = sorted(set(k["video_id"]) - set(seq_of))
    if unknown:
        raise ValueError(f"{len(unknown)} video_id(s) missing from {metadata_path}: {unknown[:5]}")
    k["id"] = k["video_id"].map(lambda v: f"{seq_of[v]:03d}")

    url_of = dict(zip(k["video_id"], k["links"]))
    groups = duplicate_groups(dup_path, include_candidates)
    member_of: dict[str, set[str]] = {v: g for g in groups for v in g}
    stray = sorted(set(member_of) - set(url_of))
    if stray:
        raise ValueError(f"{dup_path} references video_ids absent from the CSV: {stray}")

    k["duplicate_of"] = k["video_id"].map(
        lambda v: DUP_SEPARATOR.join(sorted(url_of[o] for o in member_of[v] - {v})) if v in member_of else ""
    )

    n_flagged = int((k["duplicate_of"] != "").sum())
    logging.info(f"{len(groups)} duplicate group(s) covering {n_flagged} row(s)")
    for g in groups:
        logging.info(f"  group: {sorted(g)}")

    out = k[["id", *original_cols, "video_id", "duplicate_of"]]
    if dry_run:
        logging.info("--dry-run: not writing. Preview of flagged rows:")
        for _, r in out[out["duplicate_of"] != ""].iterrows():
            logging.info(f"  id={r['id']} {r['video_id']} {r['titles']!r} -> {r['duplicate_of']}")
        return 0

    # CRLF + UTF-8 to match the file as it already exists on disk (114 of the
    # quoted fields contain embedded newlines, so this is not cosmetic).
    out.to_csv(csv_path, index=False, encoding="utf-8", lineterminator="\r\n")
    logging.info(f"wrote {len(out)} rows x {len(out.columns)} columns to {csv_path}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--csv", default=Path("kargin_eng.csv"), type=Path)
    p.add_argument("--metadata", default=Path("data/youtube_metadata.csv"), type=Path)
    p.add_argument("--duplicates", default=Path("data/duplicates.csv"), type=Path)
    p.add_argument("--include-candidates", action="store_true",
                   help="also treat verdict=candidate pairs as duplicates")
    p.add_argument("--dry-run", action="store_true", help="log what would change, write nothing")
    args = p.parse_args()
    sys.exit(main(args.csv, args.metadata, args.duplicates, args.include_candidates, args.dry_run))
