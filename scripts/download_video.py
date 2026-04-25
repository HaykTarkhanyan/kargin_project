"""Download 360p video for every video in data/youtube_metadata.csv.

Mirror of scripts/download_audio.py but for video. Same naming convention,
same resume-by-file-presence, same rate-limit auto-stop. Different output
directory (data/video/), different log file, different format selector.

Format: best[height<=360]/best. The first selector picks YouTube's classic
format 18 (single pre-merged mp4 with H.264 video + AAC audio at ~330 kbps
total) when available — no FFmpeg needed. The fallback `best` covers the
rare case where YouTube only serves split video+audio streams at 360p.

Resume-safe by file presence: any video_id that already has a file in
data/video/ is skipped on subsequent runs. Failures are logged but NOT
recorded persistently — they will be retried on the next run, which is the
desired behavior for transient rate-limit errors.

Output filenames look like:
    data/video/{seq:03d}_{sanitized_title}_{video_id}.{ext}

Usage:
    uv run python scripts/download_video.py
    uv run python scripts/download_video.py --limit 5      # smoke test
    uv run python scripts/download_video.py --sleep 1.0    # be polite
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import time
from pathlib import Path

import pandas as pd
import yt_dlp


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "download_video.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)


BOT_DETECTION_MARKERS = (
    "Sign in to confirm you're not a bot",
    "confirm your age",
)

# YouTube IDs are always 11 chars from this alphabet; anchor to the extension
# so we can recover the id from any filename shape.
_YT_ID_FROM_FILENAME = re.compile(r"([A-Za-z0-9_-]{11})\.[^.]+$")


def existing_video_ids(output_dir: Path) -> set[str]:
    """Set of video_ids already on disk (any extension, ignore part-files)."""
    if not output_dir.exists():
        return set()
    out: set[str] = set()
    for p in output_dir.iterdir():
        if not p.is_file():
            continue
        if p.suffix == ".part" or p.name.startswith("."):
            continue
        m = _YT_ID_FROM_FILENAME.search(p.name)
        if m:
            out.add(m.group(1))
    return out


def download_one(video_id: str, output_dir: Path, seq: int) -> tuple[bool, str]:
    """Try to download one video at <=360p. Returns (ok, message)."""
    outtmpl = str(output_dir / f"{seq:03d}_%(title)s_%(id)s.%(ext)s")
    ydl_opts = {
        "format": "best[height<=360]/best",
        "outtmpl": outtmpl,
        "restrictfilenames": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 2,
        "fragment_retries": 2,
        "continuedl": True,
    }
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
        ext = info.get("ext", "?")
        size = info.get("filesize") or info.get("filesize_approx") or 0
        height = info.get("height", "?")
        tbr = info.get("tbr") or "?"
        return True, f"{ext} {height}p {tbr}kbps {size:,}B"
    except yt_dlp.utils.DownloadError as e:
        return False, str(e).splitlines()[0][:300]


def main(input_csv: Path, output_dir: Path, limit: int | None, sleep_sec: float) -> int:
    if not input_csv.exists():
        logging.error(f"input not found: {input_csv}")
        return 2

    df = pd.read_csv(input_csv)
    if "video_id" not in df.columns:
        logging.error(f"{input_csv} missing 'video_id' column")
        return 2

    if "availability" in df.columns:
        non_public = df[df["availability"].fillna("public") != "public"]
        if len(non_public):
            ids = non_public["video_id"].tolist()
            logging.info(f"skipping {len(non_public)} non-public video(s): {ids}")
        df = df[df["availability"].fillna("public") == "public"]

    all_ids = df["video_id"].dropna().astype(str).tolist()
    seq_of: dict[str, int] = {vid: i for i, vid in enumerate(all_ids, 1)}

    output_dir.mkdir(parents=True, exist_ok=True)
    have = existing_video_ids(output_dir)
    todo = [vid for vid in all_ids if vid not in have]

    if limit is not None:
        todo = todo[:limit]

    logging.info(
        f"{len(all_ids)} target videos, {len(have)} already on disk, "
        f"{len(todo)} to download this run"
    )
    if not todo:
        logging.info("nothing to do")
        return 0

    ok = 0
    fail = 0
    for i, vid in enumerate(todo, 1):
        logging.info(f"[{i}/{len(todo)}] seq={seq_of[vid]:03d} {vid}")
        success, msg = download_one(vid, output_dir, seq_of[vid])
        if success:
            ok += 1
            logging.info(f"  ok: {msg}")
        else:
            fail += 1
            logging.error(f"  fail: {msg}")
            if any(marker in msg for marker in BOT_DETECTION_MARKERS):
                logging.error(
                    "rate-limited by YouTube (bot detection). "
                    "Stopping early — re-run later to resume."
                )
                break
        if sleep_sec > 0 and i < len(todo):
            time.sleep(sleep_sec)

    final_have = existing_video_ids(output_dir)
    logging.info(
        f"done. this run: {ok} ok, {fail} fail. "
        f"on disk: {len(final_have)}/{len(all_ids)}"
    )
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", default=Path("data/youtube_metadata.csv"), type=Path)
    p.add_argument("--output", default=Path("data/video"), type=Path)
    p.add_argument("--limit", type=int, default=None, help="for smoke testing")
    p.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="seconds to wait between downloads (default 0)",
    )
    args = p.parse_args()
    sys.exit(main(args.input, args.output, args.limit, args.sleep))
