"""Cut the quiz stills listed in data/quiz/stills.json out of data/video/ into web/public/quiz/.

Each entry: {"file": "l1-01.jpg", "video_id": "<youtube id>", "ts": "MM:SS", "note": "..."}.
The output file name is chosen per question (not per video) so the URL does not reveal the answer.

Usage:
  uv run python scripts/extract_quiz_stills.py
"""

import json
import logging
import subprocess
from pathlib import Path

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


def main() -> None:
    stills = json.loads(LIST.read_text(encoding="utf-8"))
    files = [s["file"] for s in stills]
    if len(files) != len(set(files)):
        raise ValueError("duplicate output file names in stills.json")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for s in stills:
        video = find_video(s["video_id"])
        dest = OUT_DIR / s["file"]
        cut(video, s["ts"], dest)
        log.info(f"{dest.relative_to(ROOT)} <- {video.name} @ {s['ts']} ({dest.stat().st_size} bytes)")
    log.info(f"wrote {len(stills)} stills to {OUT_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
