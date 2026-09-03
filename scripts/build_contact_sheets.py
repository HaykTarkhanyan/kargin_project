"""Build one contact-sheet JPEG per downloaded video in data/video/.

Each sheet is an 8x5 grid of 40 frames sampled uniformly across the video
(interval = duration / 40), tiles 320x180, sheet 2560x900. That shape was
chosen against the Claude vision limits (28 px patches, 2576 px long edge on
Fable/Opus-tier models): one sheet costs ~3,000 visual tokens however many
tiles it holds, ~3x cheaper than sending the frames loose. Sampling density
was decided 2026-09-03: fixed 40 frames regardless of length; the long tail
gets coarse and that is accepted. See DEFERRED_TODO.md for the full envelope.

Each tile carries its source timestamp (HH:MM:SS.mmm, bottom-left) burned in
via drawtext — without it a reader cannot anchor a tile to a moment.

Windows + drawtext gotcha: a `C:` drive colon inside a filter string breaks
the filter parser, so ffmpeg runs with cwd = the output dir and references a
font copied there as a bare relative `font.ttf` (same trick as
render_transcription_batch.py).

Durations come from data/youtube_metadata.csv (duration_sec by video_id) —
no per-file ffprobe. A video absent from the CSV is an ERROR, not a skip.

Resume-safe by file presence: a video whose sheet already exists is skipped,
so this can run repeatedly while download_video.py is still filling
data/video/ and a final run sweeps up the remainder.

Usage:
    uv run python scripts/build_contact_sheets.py
    uv run python scripts/build_contact_sheets.py --limit 1   # smoke test
"""

from __future__ import annotations

import argparse
import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "build_contact_sheets.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)

FRAMES = 40
COLS, ROWS = 8, 5
TILE_W, TILE_H = 320, 180
JPEG_QUALITY = "3"  # mjpeg -q:v, 2-31, lower is better
FONT_SOURCE = Path("C:/Windows/Fonts/arial.ttf")

# Same shape download_video.py recovers ids with.
_YT_ID_FROM_FILENAME = re.compile(r"([A-Za-z0-9_-]{11})\.[^.]+$")


def build_one(video: Path, out_path: Path, duration: float, out_dir: Path) -> None:
    """Render one sheet. Raises on any ffmpeg failure — no silent fallbacks."""
    interval = duration / FRAMES
    vf = (
        f"fps=1/{interval:.6f},"
        f"scale={TILE_W}:{TILE_H}:force_original_aspect_ratio=decrease,"
        f"pad={TILE_W}:{TILE_H}:(ow-iw)/2:(oh-ih)/2,"
        "drawtext=fontfile=font.ttf:text='%{pts\\:hms}':fontcolor=white:"
        "fontsize=18:x=6:y=h-th-6:box=1:boxcolor=black@0.5:boxborderw=3,"
        f"tile={COLS}x{ROWS}"
    )
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(video.resolve()),
        "-vf", vf,
        "-frames:v", "1",
        "-q:v", JPEG_QUALITY,
        out_path.name,
    ]
    # cwd=out_dir so font.ttf and the output are colon-free relative paths.
    res = subprocess.run(cmd, cwd=out_dir, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg failed ({res.returncode}): {res.stderr.strip()[:300]}")
    if not (out_dir / out_path.name).exists():
        raise RuntimeError("ffmpeg exited 0 but wrote no output")


def main(video_dir: Path, out_dir: Path, meta_csv: Path, limit: int | None) -> int:
    if not meta_csv.exists():
        logging.error(f"metadata not found: {meta_csv}")
        return 2
    df = pd.read_csv(meta_csv)
    duration_of = dict(zip(df["video_id"].astype(str), df["duration_sec"].astype(float)))

    out_dir.mkdir(parents=True, exist_ok=True)
    if not (out_dir / "font.ttf").exists():
        shutil.copy(FONT_SOURCE, out_dir / "font.ttf")

    videos = sorted(p for p in video_dir.iterdir() if p.is_file() and p.suffix == ".mp4")
    todo = [v for v in videos if not (out_dir / f"{v.stem}.jpg").exists()]
    if limit is not None:
        todo = todo[:limit]
    logging.info(f"{len(videos)} videos on disk, {len(todo)} sheets to build this run")

    ok = fail = 0
    for i, video in enumerate(todo, 1):
        m = _YT_ID_FROM_FILENAME.search(video.name)
        vid = m.group(1) if m else None
        if vid is None or vid not in duration_of:
            logging.error(f"[{i}/{len(todo)}] {video.name}: no duration in {meta_csv}")
            fail += 1
            continue
        try:
            build_one(video, out_dir / f"{video.stem}.jpg", duration_of[vid], out_dir)
            ok += 1
            logging.info(f"[{i}/{len(todo)}] ok: {video.stem}.jpg ({duration_of[vid]:.0f}s)")
        except Exception as e:
            fail += 1
            logging.error(f"[{i}/{len(todo)}] fail: {video.name}: {e}")

    logging.info(f"done. this run: {ok} ok, {fail} fail")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--videos", default=Path("data/video"), type=Path)
    p.add_argument("--out", default=Path("data/contact_sheets"), type=Path)
    p.add_argument("--meta", default=Path("data/youtube_metadata.csv"), type=Path)
    p.add_argument("--limit", type=int, default=None, help="for smoke testing")
    args = p.parse_args()
    sys.exit(main(args.videos, args.out, args.meta, args.limit))
