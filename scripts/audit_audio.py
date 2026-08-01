"""Verify that data/audio/ has exactly one usable file for every video in the archive.

Answers "do we have audio for ALL videos?" and fails loudly if not. Checks:

  1. every video_id in kargin_eng.csv has a file in data/audio/
  2. no audio file belongs to a video_id that isn't in the CSV (orphans)
  3. no video_id has two files (would make the seq->file mapping ambiguous)
  4. no file is suspiciously small (a truncated / failed download)
  5. no leftover .part files from an interrupted yt-dlp run
  6. the NNN_ filename prefix still matches row order in data/youtube_metadata.csv,
     which is what makes `id` in kargin_eng.csv point at the right audio file

Exit code 0 only if all checks pass, so this is safe to gate a pipeline on.

Usage:
    uv run python scripts/audit_audio.py
    uv run python scripts/audit_audio.py --min-bytes 200000
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "audit_audio.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

# Same shapes download_audio.py uses: ids are 11 chars, filenames are NNN_<title>_<id>.<ext>.
VIDEO_ID_FROM_URL = re.compile(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})")
AUDIO_FILENAME = re.compile(r"^(\d{3})_.*?([A-Za-z0-9_-]{11})\.[^.]+$")


def video_ids_from_csv(csv_path: Path) -> pd.Series:
    """video_id per row of kargin_eng.csv, parsed out of the `links` column."""
    df = pd.read_csv(csv_path)
    ids = df["links"].map(
        lambda u: m.group(1) if isinstance(u, str) and (m := VIDEO_ID_FROM_URL.search(u)) else None
    )
    unparseable = df.loc[ids.isna(), "links"].tolist()
    if unparseable:
        raise ValueError(f"{len(unparseable)} link(s) have no parseable video_id: {unparseable[:5]}")
    return ids


def scan_audio_dir(audio_dir: Path) -> tuple[dict[str, list[Path]], list[Path], list[Path]]:
    """Return (video_id -> files, part_files, unparseable_files)."""
    by_id: dict[str, list[Path]] = defaultdict(list)
    parts: list[Path] = []
    unparseable: list[Path] = []
    for p in sorted(audio_dir.iterdir()):
        if not p.is_file() or p.name.startswith("."):
            continue
        if p.suffix == ".part":
            parts.append(p)
            continue
        m = AUDIO_FILENAME.match(p.name)
        if m:
            by_id[m.group(2)].append(p)
        else:
            unparseable.append(p)
    return dict(by_id), parts, unparseable


def main(csv_path: Path, metadata_path: Path, audio_dir: Path, min_bytes: int) -> int:
    if not audio_dir.exists():
        logging.error(f"audio dir not found: {audio_dir}")
        return 2

    csv_ids = video_ids_from_csv(csv_path)
    wanted = set(csv_ids)
    by_id, parts, unparseable = scan_audio_dir(audio_dir)
    have = set(by_id)

    logging.info(f"{len(csv_ids)} CSV rows, {len(wanted)} distinct video_ids")
    logging.info(f"{sum(len(v) for v in by_id.values())} audio files, {len(have)} distinct video_ids")

    problems: list[str] = []

    missing = sorted(wanted - have)
    if missing:
        problems.append(f"{len(missing)} video(s) have NO audio file: {missing}")

    orphans = sorted(have - wanted)
    if orphans:
        problems.append(f"{len(orphans)} audio file(s) not referenced by the CSV: {orphans}")

    multi = {vid: [p.name for p in ps] for vid, ps in by_id.items() if len(ps) > 1}
    if multi:
        problems.append(f"{len(multi)} video(s) have more than one audio file: {multi}")

    if parts:
        problems.append(f"{len(parts)} leftover .part file(s): {[p.name for p in parts]}")

    if unparseable:
        problems.append(
            f"{len(unparseable)} file(s) whose name has no video_id: {[p.name for p in unparseable]}"
        )

    tiny = sorted(
        (p.name, p.stat().st_size)
        for ps in by_id.values()
        for p in ps
        if p.stat().st_size < min_bytes
    )
    if tiny:
        problems.append(f"{len(tiny)} file(s) smaller than {min_bytes:,}B (truncated?): {tiny}")

    # The NNN_ prefix is the 1-based row number in youtube_metadata.csv. annotate_kargin_csv.py
    # derives `id` from that same ordering, so a drift here silently mis-links rows to audio.
    meta_ids = pd.read_csv(metadata_path)["video_id"].tolist()
    drift = []
    for vid, ps in by_id.items():
        seq = int(AUDIO_FILENAME.match(ps[0].name).group(1))
        if not (1 <= seq <= len(meta_ids)) or meta_ids[seq - 1] != vid:
            drift.append((ps[0].name, seq, meta_ids[seq - 1] if 1 <= seq <= len(meta_ids) else None))
    if drift:
        problems.append(f"{len(drift)} file(s) whose NNN_ prefix disagrees with metadata row order: {drift[:5]}")

    if problems:
        for p in problems:
            logging.error(p)
        logging.error(f"FAIL: {len(problems)} problem(s)")
        return 1

    total_gb = sum(p.stat().st_size for ps in by_id.values() for p in ps) / 1024**3
    logging.info(
        f"OK: all {len(wanted)} videos have exactly one audio file, "
        f"no orphans, no truncated files, seq prefixes aligned ({total_gb:.2f} GB)"
    )
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--csv", default=Path("kargin_eng.csv"), type=Path)
    p.add_argument("--metadata", default=Path("data/youtube_metadata.csv"), type=Path)
    p.add_argument("--audio", default=Path("data/audio"), type=Path)
    p.add_argument(
        "--min-bytes",
        type=int,
        default=100_000,
        help="flag audio files smaller than this as likely truncated (default 100000)",
    )
    args = p.parse_args()
    sys.exit(main(args.csv, args.metadata, args.audio, args.min_bytes))
