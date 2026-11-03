"""
Download screening audio for candidate videos (plan steps A3 and M3,
docs/superpowers/plans/2026-11-03-extend-archive.md). Only the audio needed to match
against the archive, at low bitrate: the matcher works at 8-11 kHz mono.

  --set candidates   first 90 s of each row in data/candidates/candidates.csv
                     -> data/candidates/audio/<video_id>.<ext>
  --set pool         the whole audio of each row in data/compilations/pool.csv
                     -> data/compilations/audio/<video_id>.<ext>

Resume-safe by file presence. Paced (--sleep, default 3 s) because ~2,000 requests
will meet YouTube's bot check sooner or later; when it appears the run STOPS, so it
can be resumed later instead of hammering through. Per-video failures (removed,
private, age-restricted) are logged at ERROR and written to <set>_failures.csv with
the reason, which is data in its own right: a dead or restricted upload can't be
the archive's copy (Q8). Failures are retried on the next run.

Both audio folders are gitignored. With only 16 GB of disk free (Q9), delete a
set's audio by exact path once its matches are saved.

Usage (screening ~3-5 h for ~1,900 candidates at 3 s pacing, spread over runs, a guess):
  uv run python scripts/non_essential/screen_audio.py --set candidates --limit 3
  uv run python scripts/non_essential/screen_audio.py --set candidates
"""

from __future__ import annotations

import argparse
import csv
import logging
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yt_dlp

ROOT = Path(__file__).resolve().parents[2]
SETS = {
    "candidates": (ROOT / "data" / "candidates" / "candidates.csv", ROOT / "data" / "candidates" / "audio", 90),
    "pool": (ROOT / "data" / "compilations" / "pool.csv", ROOT / "data" / "compilations" / "audio", None),
}
# Opus ~50 kbps, then AAC 48 kbps, then whatever is smallest.
FORMAT = "249/139/worstaudio"
BOT_CHECK = "Sign in to confirm you're not a bot"
AGE_GATE = "confirm your age"
# Reasons recorded in <set>_failures.csv. Permanent ones are facts about the video; the
# rest are retried (match_candidates.is_permanent_failure reads the message the same way).
PERMANENT = (("not available", "unavailable"), ("private video", "private"), ("video unavailable", "unavailable"),
             ("please sign in", "sign_in_required"), ("removed", "removed"))
VIDEO_ID = re.compile(r"([A-Za-z0-9_-]{11})\.[^.]+$")

(ROOT / "logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(ROOT / "logs" / "screen_audio.log", encoding="utf-8")],
)
log = logging.getLogger("screen_audio")


def on_disk(folder: Path) -> set[str]:
    """video_ids with a finished file (yt-dlp writes .part until it is done)."""
    have = set()
    for p in folder.iterdir():
        if p.suffix in (".part", ".ytdl") or ".part-Frag" in p.name:
            continue
        m = VIDEO_ID.search(p.name)
        if m:
            have.add(m.group(1))
    return have


def reason_of(msg: str) -> str:
    m = msg.lower()
    if BOT_CHECK.lower() in m:
        return "bot_check"
    if AGE_GATE in m:
        return "age_restricted"
    for key, reason in PERMANENT:
        if key in m:
            return reason
    if "ffmpeg exited" in m:
        return "transient_ffmpeg"
    if "http error 403" in m:
        return "transient_http_403"
    return "transient_other"


def trim_local(src: Path, seconds: int) -> None:
    """Keep the first `seconds` of a fully downloaded file, in place."""
    import subprocess
    tmp = src.with_name(src.stem + ".trim" + src.suffix)
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-t", str(seconds), "-i", str(src), "-c", "copy", str(tmp)],
                       capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"local trim failed on {src.name}: {r.stderr.decode(errors='replace')[:200]}")
    tmp.replace(src)


def fetch(video_id: str, folder: Path, seconds: int | None) -> tuple[bool, str]:
    opts = {
        "format": FORMAT,
        "outtmpl": str(folder / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 2,
        "fragment_retries": 2,
        "continuedl": True,
    }
    if seconds:
        opts["download_ranges"] = yt_dlp.utils.download_range_func([], [[0, seconds]])
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)
        return True, f"{info.get('ext', '?')} {info.get('abr') or info.get('tbr') or '?'}kbps fmt {info.get('format_id')}"
    except yt_dlp.utils.DownloadError as e:
        msg = (str(e).splitlines() or [""])[0][:300]
        if not (seconds and reason_of(msg) == "transient_ffmpeg"):
            return False, msg
    # The partial (sectioned) download died inside ffmpeg. Measured 2026-11-03: the same
    # videos download fine whole. Retry once that way and trim locally; logged, not silent.
    log.warning(f"{video_id}: sectioned download failed in ffmpeg; retrying whole + local {seconds} s trim")
    opts.pop("download_ranges")
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)
        trim_local(folder / f"{video_id}.{info.get('ext')}", seconds)
        return True, f"{info.get('ext', '?')} fmt {info.get('format_id')} (whole + local trim)"
    except yt_dlp.utils.DownloadError as e:
        return False, (str(e).splitlines() or [""])[0][:300]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", choices=sorted(SETS), required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--series", default=None,
                    help="comma list, e.g. haghordum,multer,kaset: only rows of these series (priority runs)")
    ap.add_argument("--ids-file", type=Path, default=None,
                    help="only these video ids, one per line (e.g. gate_unclear.py's sample)")
    ap.add_argument("--sleep", type=float, default=3.0, help="seconds between requests (+ up to 1 s jitter)")
    args = ap.parse_args()

    src, folder, seconds = SETS[args.set]
    rows = pd.read_csv(src, dtype={"video_id": str})
    if args.series:
        wanted = set(args.series.split(","))
        unknown = wanted - set(rows["series"])
        if unknown:
            raise ValueError(f"no rows with series {sorted(unknown)} in {src.name}")
        rows = rows[rows["series"].isin(wanted)]
    if args.ids_file:
        ids = set(args.ids_file.read_text(encoding="utf-8").split())
        unknown = ids - set(rows["video_id"])
        if unknown:
            raise ValueError(f"{len(unknown)} ids in {args.ids_file.name} are not rows of {src.name}: {sorted(unknown)[:5]}")
        rows = rows[rows["video_id"].isin(ids)]
    folder.mkdir(parents=True, exist_ok=True)
    have = on_disk(folder)
    todo = [v for v in rows["video_id"] if v not in have]
    if args.limit is not None:
        todo = todo[: args.limit]
    log.info(f"{args.set}: {len(rows)} rows, {len(have)} on disk, {len(todo)} to fetch "
             f"({'first ' + str(seconds) + ' s' if seconds else 'whole audio'}, format {FORMAT})")
    fail_path = src.parent / f"{args.set}_failures.csv"
    new_file = not fail_path.exists()
    t0 = time.time()
    ok = fail = 0
    with open(fail_path, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new_file:
            w.writerow(["video_id", "reason", "message", "at"])
        for i, vid in enumerate(todo, 1):
            good, msg = fetch(vid, folder, seconds)
            el = time.time() - t0
            eta = el / i * (len(todo) - i)
            if good:
                ok += 1
                log.info(f"[{i}/{len(todo)}] {vid} ok: {msg}  ({el:.0f}s elapsed, ~{eta / 60:.0f} min left)")
            else:
                fail += 1
                reason = reason_of(msg)
                log.error(f"[{i}/{len(todo)}] {vid} FAILED ({reason}): {msg}")
                w.writerow([vid, reason, msg, datetime.now(timezone.utc).isoformat(timespec="seconds")])
                fh.flush()
                if reason == "bot_check":
                    log.error("YouTube's bot check is up: stopping. Resume later; nothing is lost.")
                    break
            if i < len(todo):
                time.sleep(args.sleep + random.random())
    log.info(f"done: {ok} ok, {fail} failed, {time.time() - t0:.0f}s")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
