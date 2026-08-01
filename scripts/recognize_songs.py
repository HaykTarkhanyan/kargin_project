"""Identify the music in each sketch by Shazam-ing clips of our local audio.

Why do this ourselves: YouTube will not tell us what music is in these videos.
The Data API v3 has no copyright-claim field for videos you don't own, Content ID
claims are behind the partner-only Content ID API, and yt-dlp returns 78 fields
with nothing music-related. The public "Suggested by SME/UMG" panel
(scripts/fetch_music_credits.py) covers only a small fraction. But we already
hold all 702 audio files, so we can just identify the music directly.

Method: walk each file in fixed steps, cut a short mp3 clip at each offset, and
ask Shazam. A sketch's music is usually an intro/outro sting, so uniform
sampling finds it without assuming where it sits.

ShazamIO is an UNOFFICIAL reverse-engineered client with no API key and no
published rate limit. It can break whenever Shazam changes its private service.
Be polite (--sleep) and treat failures as expected, not exceptional.

Clips are piped from ffmpeg as bytes; recognize() takes bytes directly, so no
temp files are written. mp3 is used because that is the format the original
experiment validated (experiments/song_recognition/).

Resume-safe per (video_id, start_sec): re-running only fills gaps.

Usage:
    uv run --group songs python scripts/recognize_songs.py --limit 5
    uv run --group songs python scripts/recognize_songs.py --ids AXFZ8ymj--w,5sXTp5UE-Vg
    uv run --group songs python scripts/recognize_songs.py --every 20 --sleep 1.5
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "recognize_songs.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

# shazamio-core's Rust layer logs a few INFO lines per clip ("found the format
# marker", "estimating duration from bitrate") which bury our own output.
for _noisy in ("shazamio", "shazamio_core", "pydub"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

AUDIO_FILENAME = re.compile(r"^(\d{3})_.*?([A-Za-z0-9_-]{11})\.[^.]+$")

# Kargin Haghordum aired 2003-09-06 to 2009-12-26. The YouTube uploads are archive
# dumps years later -- all 702 went up on just 9 distinct dates, 343 of them on
# 2012-12-28 -- so upload_date says almost nothing about when a sketch was filmed.
# Music in a sketch had to exist when it was FILMED, which is the tighter bound.
PRODUCTION_END_YEAR = 2009

SCHEMA = [
    "video_id", "start_sec", "matched",
    "artist", "title", "album", "label", "released", "genre",
    "isrc", "shazam_key", "shazam_url",
    "upload_year", "released_year", "after_production_end",
    "recognized_at", "error",
]


def year_of(value) -> int | None:
    """Leading 4-digit year out of '2005', '2005.0', '20121228.0', etc."""
    m = re.match(r"(\d{4})", str(value).strip())
    return int(m.group(1)) if m else None


def audio_paths(audio_dir: Path) -> dict[str, Path]:
    return {
        m.group(2): p
        for p in sorted(audio_dir.iterdir())
        if p.is_file() and (m := AUDIO_FILENAME.match(p.name))
    }


def clip_bytes(path: Path, start: float, duration: float) -> bytes:
    """A short mono 44.1 kHz mp3 clip, straight to memory. -ss before -i seeks fast."""
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(duration), "-i", str(path),
         "-vn", "-ac", "1", "-ar", "44100", "-b:a", "128k", "-f", "mp3", "-"],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed at {start}s: {proc.stderr.decode(errors='replace')[:200]}")
    if not proc.stdout:
        raise RuntimeError(f"ffmpeg produced an empty clip at {start}s")
    return proc.stdout


def flatten_track(track: dict) -> dict:
    """Pull the useful fields out of Shazam's nested track object.

    Album / Label / Released live in sections[].metadata as {title, text} pairs
    rather than as named fields, so they have to be collected by label.
    """
    meta = {}
    for section in track.get("sections") or []:
        for m in section.get("metadata") or []:
            if m.get("title"):
                meta[m["title"]] = m.get("text")
    return {
        "artist": track.get("subtitle"),
        "title": track.get("title"),
        "album": meta.get("Album"),
        "label": meta.get("Label"),
        "released": meta.get("Released"),
        "genre": (track.get("genres") or {}).get("primary"),
        "isrc": track.get("isrc"),
        "shazam_key": track.get("key"),
        "shazam_url": track.get("url"),
    }


def clip_starts(duration_sec: float, every: int, clip_len: float, max_clips: int | None) -> list[int]:
    """Offsets to sample. Stops far enough from the end to get a full-length clip."""
    last = max(0, int(duration_sec - clip_len))
    starts = list(range(0, last + 1, every)) or [0]
    return starts[:max_clips] if max_clips else starts


async def run(todo: list[tuple[str, int]], paths: dict[str, Path],
              clip_len: float, sleep_sec: float, out_path: Path,
              rows: dict[tuple[str, int], dict],
              upload_year: dict[str, int], production_end: int) -> tuple[int, int, int, int]:
    from shazamio import Shazam

    shazam = Shazam()
    ok = fail = hits = impossible = 0
    for i, (vid, start) in enumerate(todo, 1):
        row = {k: "" for k in SCHEMA}
        row.update({"video_id": vid, "start_sec": start, "matched": False,
                    "recognized_at": pd.Timestamp.now("UTC").isoformat(timespec="seconds")})
        try:
            data = clip_bytes(paths[vid], start, clip_len)
            result = await shazam.recognize(data)
            track = result.get("track")
            ok += 1
            if track:
                hits += 1
                row.update(flatten_track(track))
                row["matched"] = True

                # Music in a sketch had to exist when it was filmed. Flag matches
                # dated after the show stopped production -- a cheap first filter
                # on the spurious hits that acoustic matching against ~100M tracks
                # always produces on speech and laugh tracks.
                #
                # NOT proof on its own: Shazam reports the date of the RELEASE it
                # matched, which may be a later compilation of a much older
                # recording (Andrei Petrov's 1979 film cue matches a 2005 "Best
                # of" here). So this marks a match for review, not for deletion.
                ry = year_of(row["released"]) if row["released"] else None
                row["upload_year"] = upload_year.get(vid) or ""
                row["released_year"] = ry or ""
                row["after_production_end"] = bool(ry and ry > production_end)

                flag = ""
                if row["after_production_end"]:
                    impossible += 1
                    flag = f"  <-- SUSPECT: released {ry} > production ended {production_end}"
                logging.info(f"[{i}/{len(todo)}] {vid} @{start:>4}s  {row['artist']} - {row['title']}"
                             f"   [{row['label']}, {row['released']}]{flag}")
            else:
                row["upload_year"] = upload_year.get(vid) or ""
                row["released_year"] = ""
                row["after_production_end"] = False
                logging.info(f"[{i}/{len(todo)}] {vid} @{start:>4}s  no match")
        except Exception as e:
            fail += 1
            row["error"] = f"{type(e).__name__}: {str(e).splitlines()[0][:200]}"
            logging.error(f"[{i}/{len(todo)}] {vid} @{start}s failed: {row['error']}")

        rows[(vid, start)] = row
        if i % 20 == 0 or i == len(todo):
            write(rows, out_path)
        if sleep_sec > 0 and i < len(todo):
            time.sleep(sleep_sec)
    return ok, fail, hits, impossible


def write(rows: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(list(rows.values()), columns=SCHEMA)
    df = df.sort_values(["video_id", "start_sec"])
    df.to_csv(out_path, index=False, encoding="utf-8")


def main(metadata: Path, audio_dir: Path, out_path: Path, ids: str | None,
         limit: int | None, every: int, clip_len: float, max_clips: int | None,
         sleep_sec: float, production_end: int) -> int:
    m = pd.read_csv(metadata)
    paths = audio_paths(audio_dir)

    if ids:
        wanted = [v.strip() for v in ids.split(",") if v.strip()]
        m = m[m["video_id"].isin(wanted)]
        if missing := sorted(set(wanted) - set(m["video_id"])):
            logging.error(f"unknown video_id(s): {missing}")
            return 2
    if limit is not None:
        m = m.head(limit)

    if no_audio := sorted(set(m["video_id"]) - set(paths)):
        logging.error(f"{len(no_audio)} video(s) have no audio file: {no_audio[:5]}")
        return 2

    rows: dict[tuple[str, int], dict] = {}
    if out_path.exists():
        prior = pd.read_csv(out_path)
        for col in SCHEMA:
            if col not in prior.columns:
                prior[col] = ""
        for r in prior[SCHEMA].to_dict("records"):
            # Only completed clips count as done; errored ones get retried.
            if str(r.get("error") or "").strip() in ("", "nan"):
                rows[(str(r["video_id"]), int(r["start_sec"]))] = r
        logging.info(f"resume: {len(rows)} clips already recognized")

    todo: list[tuple[str, int]] = []
    for _, r in m.iterrows():
        vid = str(r["video_id"])
        for s in clip_starts(float(r["duration_sec"]), every, clip_len, max_clips):
            if (vid, s) not in rows:
                todo.append((vid, s))

    logging.info(
        f"{len(m)} video(s), {len(todo)} clip(s) to recognize "
        f"({clip_len:g}s every {every}s, {sleep_sec}s between calls)"
    )
    if not todo:
        logging.info("nothing to do")
        return 0

    upload_year = {str(r["video_id"]): y for _, r in m.iterrows()
                   if (y := year_of(r["upload_date"]))}

    t0 = time.time()
    ok, fail, hits, suspect = asyncio.run(
        run(todo, paths, clip_len, sleep_sec, out_path, rows, upload_year, production_end))
    write(rows, out_path)
    logging.info(
        f"done in {time.time() - t0:.0f}s. {ok} recognized, {fail} failed, "
        f"{hits} matched a song ({suspect} dated after production ended in "
        f"{production_end}) -> {out_path}"
    )
    return 1 if fail else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--metadata", default=Path("data/youtube_metadata.csv"), type=Path)
    p.add_argument("--audio", default=Path("data/audio"), type=Path)
    p.add_argument("--out", default=Path("data/song_matches.csv"), type=Path)
    p.add_argument("--ids", default=None, help="comma-separated video_ids (default: all)")
    p.add_argument("--limit", type=int, default=None, help="first N videos")
    p.add_argument("--every", type=int, default=30, help="seconds between clip starts")
    p.add_argument("--duration", type=float, default=12.0, help="clip length in seconds")
    p.add_argument("--max-clips", type=int, default=None, help="cap clips per video")
    p.add_argument("--sleep", type=float, default=1.0, help="seconds between Shazam calls")
    p.add_argument("--production-end-year", type=int, default=PRODUCTION_END_YEAR,
                   help=f"flag matches released after this year (default {PRODUCTION_END_YEAR}, "
                        "the year the show stopped airing)")
    args = p.parse_args()
    sys.exit(main(args.metadata, args.audio, args.out, args.ids, args.limit,
                  args.every, args.duration, args.max_clips, args.sleep,
                  args.production_end_year))
