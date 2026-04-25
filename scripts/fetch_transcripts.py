"""Fetch YouTube transcripts/subtitles for every video in data/youtube_metadata.csv.

Pulls both manual subs (rare for our archive — the API said zero) and the
auto-generated source-language caption only. yt-dlp's `subtitleslangs` option
accepts regex patterns; `.*-orig` matches the YouTube-internal tag for the
source-language STT track (e.g. `hy-orig`, `tr-orig`). We skip the ~156
auto-translated derivatives per video — they're Google Translate of the source,
not independent transcriptions, so they're noise.

n=30 probe showed source langs: hy (37%), tr (25%), en (19%), ro (13%), ar (6%).
For non-Armenian sources, the text is YouTube mishearing the song intro, but
timestamps are still real and tied to speech segments.

No video/audio download — just the caption text files.

Output:
    data/transcripts/{seq:03d}_{title}_{video_id}.{lang}.{ext}
        for each available caption track (json3 preferred, vtt fallback)
    data/transcripts/{seq:03d}_{title}_{video_id}.no_captions
        empty sentinel file if the video has no captions in the requested langs
        (so subsequent runs skip it instead of re-attempting)

Resume-safe: any video_id that already has at least one matching file in
data/transcripts/ is skipped. Single-threaded to avoid YouTube's bot
detection (per LEARNINGS — concurrency triggers it, not request count).

Usage:
    uv run python scripts/fetch_transcripts.py
    uv run python scripts/fetch_transcripts.py --limit 5      # smoke test
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
LOG_FILE = LOG_DIR / "fetch_transcripts.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)


BOT_DETECTION_MARKERS = (
    "Sign in to confirm you're not a bot",
    "confirm your age",
)

SUB_LANGS = [".*-orig"]  # regex; yt-dlp tags source-lang STT with `<lang>-orig`
SUB_FORMAT = "json3/vtt/srv3/srv2/srv1/ttml/best"

# Filenames look like 001_Title_<id>.hy.json3, 001_Title_<id>.no_captions, etc.
# The id is always preceded by `_` and followed by `.`. Bare `_` separators
# inside the title are fine because we anchor on the exact 11-char id alphabet.
_ID_FROM_FILENAME = re.compile(r"_([A-Za-z0-9_-]{11})\.")


def existing_video_ids(output_dir: Path) -> set[str]:
    """Set of video_ids that already have at least one transcript or sentinel file."""
    if not output_dir.exists():
        return set()
    out: set[str] = set()
    for p in output_dir.iterdir():
        if not p.is_file():
            continue
        if p.suffix == ".part" or p.name.startswith("."):
            continue
        m = _ID_FROM_FILENAME.search(p.name)
        if m:
            out.add(m.group(1))
    return out


def fetch_one(video_id: str, output_dir: Path, seq: int) -> tuple[bool, str, list[str]]:
    """Fetch all available subs for one video. Returns (ok, message, langs_written).

    langs_written lists the language codes that yt-dlp actually wrote files for
    on disk, so the caller can decide whether to drop a sentinel.
    """
    outtmpl = str(output_dir / f"{seq:03d}_%(title)s_%(id)s.%(ext)s")
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": SUB_LANGS,
        "subtitlesformat": SUB_FORMAT,
        "outtmpl": outtmpl,
        "restrictfilenames": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 2,
    }
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as e:
        return False, str(e).splitlines()[0][:300], []

    # yt-dlp doesn't return a clean list of written sub files in info, so scan disk.
    written: list[str] = []
    for p in output_dir.iterdir():
        if not p.is_file():
            continue
        # Match files for THIS video_id only
        m = _ID_FROM_FILENAME.search(p.name)
        if m and m.group(1) == video_id and p.suffix != ".no_captions":
            # Lang code sits between the id and the extension: <stem>.<lang>.<ext>
            parts = p.name.rsplit(".", 2)
            if len(parts) == 3:
                written.append(parts[1])
    written = sorted(set(written))
    return True, f"langs: {written or '(none)'}", written


def write_no_captions_sentinel(
    video_id: str, output_dir: Path, seq: int, title: str
) -> None:
    """Drop an empty marker file so future runs skip this video."""
    # Sanitize title to match yt-dlp's restrictfilenames behavior loosely.
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", title).strip("_")[:80]
    name = f"{seq:03d}_{safe}_{video_id}.no_captions"
    (output_dir / name).touch()


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
            logging.info(
                f"skipping {len(non_public)} non-public video(s): "
                f"{non_public['video_id'].tolist()}"
            )
        df = df[df["availability"].fillna("public") == "public"]

    all_ids = df["video_id"].dropna().astype(str).tolist()
    seq_of: dict[str, int] = {vid: i for i, vid in enumerate(all_ids, 1)}
    title_of: dict[str, str] = dict(zip(df["video_id"].astype(str), df["title"].fillna("")))

    output_dir.mkdir(parents=True, exist_ok=True)
    have = existing_video_ids(output_dir)
    todo = [vid for vid in all_ids if vid not in have]

    if limit is not None:
        todo = todo[:limit]

    logging.info(
        f"{len(all_ids)} target videos, {len(have)} already attempted, "
        f"{len(todo)} to fetch this run. langs={SUB_LANGS}"
    )
    if not todo:
        logging.info("nothing to do")
        return 0

    ok = 0
    fail = 0
    with_subs = 0
    no_subs = 0
    for i, vid in enumerate(todo, 1):
        logging.info(f"[{i}/{len(todo)}] seq={seq_of[vid]:03d} {vid}")
        success, msg, langs = fetch_one(vid, output_dir, seq_of[vid])
        if success:
            ok += 1
            logging.info(f"  ok: {msg}")
            if langs:
                with_subs += 1
            else:
                no_subs += 1
                write_no_captions_sentinel(
                    vid, output_dir, seq_of[vid], title_of.get(vid, "")
                )
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

    logging.info(
        f"done. ok={ok} ({with_subs} with subs, {no_subs} none), fail={fail}. "
        f"langs requested: {SUB_LANGS}"
    )
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", default=Path("data/youtube_metadata.csv"), type=Path)
    p.add_argument("--output", default=Path("data/transcripts"), type=Path)
    p.add_argument("--limit", type=int, default=None, help="for smoke testing")
    p.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="seconds to wait between fetches (default 0)",
    )
    args = p.parse_args()
    sys.exit(main(args.input, args.output, args.limit, args.sleep))
