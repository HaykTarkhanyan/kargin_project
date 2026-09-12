"""Cut the quiz stills listed in data/quiz/stills.json out of data/video/ into web/public/quiz/.

Each entry: {"file": "l1-01.jpg", "video_id": "<youtube id>", "ts": "MM:SS", "note": "..."}.
An entry with "thumbnail": true downloads the video's YouTube thumbnail instead of cutting a frame;
that is how a video outside the archive (no file under data/video/) gets a picture.
The output file name is chosen per question (not per video) so the URL does not reveal the answer.

Usage:
  uv run python scripts/extract_quiz_stills.py
"""

import json
import logging
import subprocess
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
LIST = ROOT / "data" / "quiz" / "stills.json"
VIDEO_DIR = ROOT / "data" / "video"
OUT_DIR = ROOT / "web" / "public" / "quiz"
WIDTH = 640
JPEG_QUALITY = "4"  # ffmpeg -q:v scale, 2 (best) .. 31; 4 lands around 40-60 KB at 640 px


def setup_logging() -> logging.Logger:
    Path(ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(ROOT / "logs" / "extract_quiz_stills.log", encoding="utf-8"),
        ],
    )
    return logging.getLogger(__name__)


log = setup_logging()


def find_video(video_id: str) -> Path:
    matches = list(VIDEO_DIR.glob(f"*_{video_id}.mp4"))
    if len(matches) != 1:
        raise FileNotFoundError(f"expected exactly one video for {video_id} in {VIDEO_DIR}, found {matches}")
    return matches[0]


def cut(video: Path, ts: str, dest: Path) -> None:
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", ts, "-i", str(video),
        "-frames:v", "1", "-vf", f"scale={WIDTH}:-2", "-q:v", JPEG_QUALITY,
        str(dest),
    ]
    subprocess.run(cmd, check=True)
    if not dest.exists() or dest.stat().st_size == 0:
        raise RuntimeError(f"ffmpeg produced no output for {video.name} at {ts}")


def download_thumbnail(video_id: str, dest: Path) -> None:
    r = requests.get(f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg", timeout=30)
    r.raise_for_status()
    if not r.headers.get("content-type", "").startswith("image/"):
        raise RuntimeError(f"no thumbnail image for {video_id}: content-type {r.headers.get('content-type')!r}")
    dest.write_bytes(r.content)


def main() -> None:
    stills = json.loads(LIST.read_text(encoding="utf-8"))
    files = [s["file"] for s in stills]
    if len(files) != len(set(files)):
        raise ValueError("duplicate output file names in stills.json")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for s in stills:
        dest = OUT_DIR / s["file"]
        if s.get("thumbnail"):
            download_thumbnail(s["video_id"], dest)
            log.info(f"{dest.relative_to(ROOT)} <- youtube thumbnail {s['video_id']} ({dest.stat().st_size} bytes)")
            continue
        video = find_video(s["video_id"])
        cut(video, s["ts"], dest)
        log.info(f"{dest.relative_to(ROOT)} <- {video.name} @ {s['ts']} ({dest.stat().st_size} bytes)")
    log.info(f"wrote {len(stills)} stills to {OUT_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
