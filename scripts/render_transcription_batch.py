"""Render the batch manifest into one uploadable video for YouTube ASR.

Reads data/transcription_batch/manifest.csv and produces a single mp4: the
clips' audio concatenated in manifest order, over a black background that shows
which clip is playing.

The on-screen card is for HUMAN verification only. Captions are generated from
audio, so nothing on screen reaches the transcript -- splitting the returned
caption track back into per-video pieces is done purely with the manifest's
start_sec/end_sec. That is why this script verifies the rendered duration
against the manifest total and fails if they disagree: a drift of even a few
seconds would misattribute dialogue to the neighbouring sketch.

Card text is deliberately ASCII (sequence, curation id, video id). ffmpeg's
drawtext treats ':' as its own separator and needs Armenian titles escaped, and
a mis-escaped title is a silent rendering failure, so titles stay out of it and
live in the chapter file instead.

Stages, all sequential and restartable (existing outputs are reused):
    1. normalise each clip's audio to one codec/rate
    2. concat them (stream copy) into a single track
    3. render one still card per clip
    4. mux cards + audio into the upload

Usage:
    uv run python scripts/render_transcription_batch.py
    uv run python scripts/render_transcription_batch.py --force
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "render_transcription_batch.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

# Uniform target for every clip. The sources are a mix of opus-in-webm and AAC,
# and the concat demuxer can only stream-copy when codec, rate and channel count
# all agree -- so they are made to agree once, here.
SAMPLE_RATE = 48000
CHANNELS = 2
AUDIO_BITRATE = "128k"

# Capped so a long render cannot saturate the machine while other work runs.
THREADS = "2"

FONT_SRC = Path("C:/Windows/Fonts/arial.ttf")


def run(cmd: list[str], cwd: Path | None = None) -> None:
    """Run ffmpeg, raising with its stderr on failure. Never silently continues."""
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          cwd=str(cwd) if cwd else None)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-8:])
        raise RuntimeError(f"{cmd[0]} failed ({proc.returncode}):\n{tail}")


def duration_of(path: Path) -> float:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", str(path)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {path.name}: {proc.stderr.strip()}")
    return float(json.loads(proc.stdout)["format"]["duration"])


def normalise(rows: list[dict], work: Path, force: bool) -> list[Path]:
    out_dir = work / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    outs = []
    for r in rows:
        dest = out_dir / f"{r['seq']:03d}.m4a"
        if force or not dest.exists():
            run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                 "-threads", THREADS, "-i", r["audio_path"], "-vn",
                 "-ac", str(CHANNELS), "-ar", str(SAMPLE_RATE),
                 "-c:a", "aac", "-b:a", AUDIO_BITRATE, str(dest)])
        outs.append(dest)
        # Also report the final clip: a batch of fewer than 10 would otherwise
        # print nothing between "stage 1/4" and "stage 2/4" and look hung for
        # minutes. batch02 (6 clips) went quiet for 10.
        if r["seq"] % 10 == 0 or r["seq"] == len(rows):
            logging.info(f"normalised {r['seq']}/{len(rows)}")
    return outs


def concat_audio(parts: list[Path], work: Path) -> Path:
    listing = work / "audio_list.txt"
    # Forward slashes and -safe 0: the concat demuxer's own parser chokes on
    # Windows backslashes.
    listing.write_text(
        "".join(f"file '{p.resolve().as_posix()}'\n" for p in parts), encoding="utf-8")
    merged = work / "merged.m4a"
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(merged)])
    return merged


def write_filter_script(rows: list[dict], work: Path) -> Path:
    """One drawtext per clip, gated on absolute output time.

    An earlier version rendered a PNG per clip and fed them to the concat
    demuxer with `duration` directives. That measured 6369s of video against
    6177.5s of audio -- the demuxer's per-entry durations do not accumulate to
    their sum, so every card drifted further behind the audio. Frame
    quantisation at 1 fps accounted for only 14.5s of the 191.5s gap.

    `enable='between(t,start,end)'` reads the timestamp the frame will actually
    carry, so a card is on screen for exactly its clip's window no matter what
    the encoder does with framerate. Nothing accumulates, so nothing drifts.

    Written to a file rather than passed as an argument: 30 filters exceed a
    comfortable command line, and ffmpeg parses `-filter_script` identically.
    """
    # Copied here so drawtext can use a relative path: an absolute Windows path
    # puts a ':' inside the filter string, where drawtext parses it as its own
    # option separator.
    font = work / "font.ttf"
    if not font.exists():
        shutil.copy2(FONT_SRC, font)

    def draw(text: str, size: int, y: int, r: dict) -> str:
        return (f"drawtext=fontfile=font.ttf:text='{text}':fontcolor=white:"
                f"fontsize={size}:x=(w-text_w)/2:y={y}:"
                f"enable='between(t\\,{r['start_sec']}\\,{r['end_sec']})'")

    parts = []
    for r in rows:
        # ASCII only. Armenian titles would need escaping inside the filter
        # string, and a mis-escaped title fails silently -- they live in
        # chapters.txt instead.
        parts.append(draw(f"{r['seq']:02d} / {len(rows)}", 96, 240, r))
        parts.append(draw(f"id {r['id']}", 56, 380, r))
        parts.append(draw(r["video_id"], 64, 470, r))

    script = work / "filter.txt"
    script.write_text(",".join(parts), encoding="utf-8")
    return script


def write_chapters(rows: list[dict], out_dir: Path) -> Path:
    """YouTube description chapters, so the upload is navigable by sketch."""
    def stamp(sec: float) -> str:
        s = int(sec)
        h, m, s = s // 3600, (s % 3600) // 60, s % 60
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

    dest = out_dir / "chapters.txt"
    dest.write_text(
        "".join(f"{stamp(r['start_sec'])} {r['seq']:02d} - {r['video_id']} - {r['title']}\n"
                for r in rows),
        encoding="utf-8")
    return dest


def main(manifest_path: Path, out_dir: Path, force: bool) -> int:
    if not manifest_path.exists():
        logging.error(f"no manifest at {manifest_path} -- run build_transcription_batch.py first")
        return 2
    rows = pd.read_csv(manifest_path).to_dict("records")
    expected = sum(r["duration_sec"] for r in rows)
    logging.info(f"{len(rows)} clips, {expected/3600:.2f} h expected")

    work = out_dir / "work"
    work.mkdir(parents=True, exist_ok=True)

    logging.info("stage 1/4: normalising audio")
    parts = normalise(rows, work, force)

    logging.info("stage 2/4: concatenating audio")
    merged = concat_audio(parts, work)
    got = duration_of(merged)
    if abs(got - expected) > 1.0:
        raise RuntimeError(
            f"merged audio is {got:.1f}s but the manifest says {expected:.1f}s. "
            "Offsets would be wrong, so the transcript could not be split reliably.")
    logging.info(f"merged audio {got/3600:.2f} h (matches manifest within 1s)")

    logging.info("stage 3/4: building the card filter")
    write_filter_script(rows, work)

    logging.info("stage 4/4: muxing the upload")
    final = out_dir / "batch_for_youtube.mp4"
    # cwd=work so `filter.txt` and the font inside it resolve as relative paths.
    # -t bounds the otherwise infinite colour source to exactly the audio length,
    # which is what keeps video and audio the same duration by construction.
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-threads", THREADS,
         "-f", "lavfi", "-i", "color=c=black:s=1280x720:r=1",
         "-i", str(merged.resolve()),
         "-filter_script:v", "filter.txt",
         "-t", f"{expected:.3f}",
         "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
         "-crf", "30", "-pix_fmt", "yuv420p", "-c:a", "copy",
         str(final.resolve())], cwd=work)

    final_dur = duration_of(final)
    if abs(final_dur - expected) > 2.0:
        raise RuntimeError(
            f"rendered video is {final_dur:.1f}s but should be {expected:.1f}s")

    chapters = write_chapters(rows, out_dir)
    size_mb = final.stat().st_size / 1024 / 1024
    logging.info(f"wrote {final}  ({size_mb:.0f} MB, {final_dur/3600:.2f} h)")
    logging.info(f"wrote {chapters}  (paste into the video description for chapters)")
    logging.info("UPLOAD AS UNLISTED AND SET THE AUDIO LANGUAGE TO ARMENIAN (hy) -- "
                 "letting YouTube auto-detect is exactly what produced the Turkish "
                 "and Romanian transcripts already in the archive.")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--manifest", default=Path("data/transcription_batch/manifest.csv"), type=Path)
    p.add_argument("--out", default=Path("data/transcription_batch"), type=Path)
    p.add_argument("--force", action="store_true", help="re-render cached intermediates")
    a = p.parse_args()
    sys.exit(main(a.manifest, a.out, a.force))
