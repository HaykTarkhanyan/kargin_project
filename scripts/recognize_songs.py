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
from collections import Counter
from pathlib import Path

import pandas as pd

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

class _DropLibraryChatter(logging.Filter):
    """Drop sub-warning records from the audio stack.

    shazamio-core emits three INFO lines per clip from its Rust layer ("found
    the format marker", "estimating duration from bitrate") which bury our own
    output. setLevel() does NOT stop them: pyo3-log builds a LogRecord and calls
    Logger.handle(), which skips the level check, so the filter has to sit on the
    handler instead.
    """

    NOISY = ("shazamio", "pydub", "symphonia")

    def filter(self, record: logging.LogRecord) -> bool:
        return not (record.name.startswith(self.NOISY) and record.levelno < logging.WARNING)


_handlers = [
    logging.FileHandler(LOG_DIR / "recognize_songs.log", encoding="utf-8"),
    logging.StreamHandler(),
]
for _h in _handlers:
    _h.addFilter(_DropLibraryChatter())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=_handlers,
)

# A long network loop must not burn through the whole work list when the link
# drops -- a wifi outage mid-run produced DNS failures that would have "processed"
# all 1802 clips in minutes. Resume is per-clip, so stopping early loses nothing.
FAILURE_STREAK_LIMIT = 15

AUDIO_FILENAME = re.compile(r"^(\d{3})_.*?([A-Za-z0-9_-]{11})\.[^.]+$")

# Deliberately no date-based filtering. `upload_date` is an archive-dump
# timestamp, not a production date (all 702 videos went up on 9 distinct dates),
# and the real filming dates are not known per sketch -- so any year cutoff would
# be an assumption that silently discards real matches. Shazam's `released` field
# is recorded as-is for review; it is the date of the RELEASE matched, which may
# be a much later compilation of an older recording anyway.
SCHEMA = [
    "video_id", "start_sec", "matched",
    "artist", "title", "album", "label", "released", "genre",
    "isrc", "shazam_key", "shazam_url",
    "attempts", "agree", "verdict", "stable", "alt_matches",
    "recognized_at", "error",
]

# Verdicts from the shifted-window check (see recognize_clip):
#   confirmed     two or more windows named the same track
#   contradicted  another window named a DIFFERENT track -- likely noise
#   inconclusive  the clip matched, but the shifted window found nothing; absence
#                 is not contradiction, the shift may have slid past the end of a
#                 short sting
#   no_match      nothing was found in the first place -- kept distinct from
#                 `inconclusive` so "found nothing" is never confused with
#                 "found something I could not verify"
CONFIRMED, CONTRADICTED, INCONCLUSIVE, NO_MATCH = (
    "confirmed", "contradicted", "inconclusive", "no_match")

_PAREN = re.compile(r"\s*[(\[].*$")


def identity(flat: dict) -> tuple[str, str]:
    """Artist + title with any parenthetical suffix stripped.

    Shazam holds the same recording under several entries -- "Песенка о медведях
    (Где-то на белом свете)" and "... (Remastered 2024)" are one song with two
    keys, as are "The Pink Panther Theme" and "... (From The Pink Panther)
    (Official Audio)". Comparing raw keys would call those a disagreement.
    """
    artist = str(flat.get("artist") or "").strip().casefold()
    title = _PAREN.sub("", str(flat.get("title") or "")).strip().casefold()
    return artist, title


def audio_paths(audio_dir: Path) -> dict[str, Path]:
    return {
        m.group(2): p
        for p in sorted(audio_dir.iterdir())
        if p.is_file() and (m := AUDIO_FILENAME.match(p.name))
    }


async def clip_bytes(path: Path, start: float, duration: float) -> bytes:
    """A short mono 44.1 kHz mp3 clip, straight to memory. -ss before -i seeks fast.

    Spawned via asyncio rather than subprocess.run: a blocking call here would
    stall the event loop and make --concurrency meaningless, since no other
    clip's Shazam request could progress while ffmpeg ran.
    """
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-v", "error", "-ss", str(start), "-t", str(duration), "-i", str(path),
        "-vn", "-ac", "1", "-ar", "44100", "-b:a", "128k", "-f", "mp3", "-",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed at {start}s: {err.decode(errors='replace')[:200]}")
    if not out:
        raise RuntimeError(f"ffmpeg produced an empty clip at {start}s")
    return out


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


async def recognize_clip(shazam, path: Path, start: int, clip_len: float,
                         attempts: int, shift: float, sleep_sec: float,
                         timeout: float = 45.0):
    """Recognize TIME-SHIFTED windows of the same region and report agreement.

    Returns (track_dict|None, n_attempts, agree, alt_summary).

    Why shifted rather than repeated: re-sending identical bytes proves nothing.
    The signature is computed deterministically and the service answers the same
    way, so an identical query always "agrees" with itself -- verified here, a
    clip known to be spurious came back 2/2 on repeat.

    Shifting varies the evidence instead. Real music is continuous, so a window
    slid a few seconds still contains the same recording and matches the same
    track. A hit driven by the particular speech and laughter in one window does
    not survive moving it. Same idea as the offset search in detect_duplicates.py.

    A no-match on the first window ends the clip -- there is no positive claim to
    verify, and probing every silent stretch would multiply the run for nothing.
    """
    by_id: dict[tuple[str, str], dict] = {}
    ids: list[tuple[str, str] | None] = []

    for attempt in range(attempts):
        if attempt and sleep_sec > 0:
            await asyncio.sleep(sleep_sec)   # not time.sleep: that stalls every worker
        data = await clip_bytes(path, start + attempt * shift, clip_len)
        # Hard timeout. shazamio sits on aiohttp_retry, which retries transparently
        # with backoff -- so throttling shows up as ever-slower calls, never as an
        # error. Without this, a throttled run looks like a hang: 268 clips at
        # concurrency 5 produced ZERO completions and the circuit breaker, which
        # only counts failures, had nothing to count.
        track = (await asyncio.wait_for(shazam.recognize(data), timeout)).get("track")
        if not track:
            ids.append(None)
            if attempt == 0:
                return None, 1, 0, NO_MATCH, ""
            continue
        flat = flatten_track(track)
        ident = identity(flat)
        by_id.setdefault(ident, flat)
        ids.append(ident)

    found = [i for i in ids if i]
    if not found:
        # Every window came back empty. Reachable when a later window is the only
        # one that matched and it yields no usable identity; most_common(1)[0]
        # would IndexError on the empty counter, which crashed a 485-clip run.
        return None, len(ids), 0, NO_MATCH, ""

    winner, agree = Counter(found).most_common(1)[0]
    others = [i for i in ids if i != winner]

    if agree >= 2:
        verdict = CONFIRMED
    elif any(others):                 # a different track came back -> real conflict
        verdict = CONTRADICTED
    else:                             # only no-matches -> absence, not conflict
        verdict = INCONCLUSIVE

    alt = "; ".join((by_id[i]["title"] or " - ".join(i)) if i else "no match" for i in others)
    return by_id[winner], len(ids), agree, verdict, alt


async def run(todo: list[tuple[str, int]], paths: dict[str, Path],
              clip_len: float, sleep_sec: float, out_path: Path,
              rows: dict[tuple[str, int], dict], attempts: int,
              shift: float, concurrency: int, timeout: float) -> tuple[int, int, int, int]:
    """Recognize every clip in `todo`, up to `concurrency` at a time.

    Each clip is mostly spent waiting on Shazam, so overlapping them is nearly
    free. The whole pipeline had to become genuinely non-blocking for this to
    help: ffmpeg via create_subprocess_exec and asyncio.sleep, since a single
    blocking call stalls every other worker on the same event loop.

    Counters live in a dict rather than closure locals because asyncio callbacks
    cannot rebind them. No lock is needed around the shared dicts -- asyncio is
    single-threaded and none of the updates await partway through.
    """
    from shazamio import Shazam

    shazam = Shazam()
    sem = asyncio.Semaphore(concurrency)
    st = {"ok": 0, "fail": 0, "hits": 0, "stable": 0, "streak": 0, "done": 0, "abort": False}
    total = len(todo)

    async def one(vid: str, start: int) -> None:
        if st["abort"]:
            return
        async with sem:
            if st["abort"]:
                return
            row = {k: "" for k in SCHEMA}
            row.update({"video_id": vid, "start_sec": start, "matched": False,
                        "recognized_at": pd.Timestamp.now("UTC").isoformat(timespec="seconds")})
            try:
                track, n_att, agree, verdict, alt = await recognize_clip(
                    shazam, paths[vid], start, clip_len, attempts, shift, sleep_sec, timeout)
                st["ok"] += 1
                st["streak"] = 0
                row.update({"attempts": n_att, "agree": agree, "verdict": verdict,
                            "alt_matches": alt})
                if track:
                    st["hits"] += 1
                    row.update(track)
                    row["matched"] = True
                    row["stable"] = verdict == CONFIRMED
                    if row["stable"]:
                        st["stable"] += 1
                    mark = "" if row["stable"] else f"  <-- {verdict.upper()} ({agree}/{n_att}), also: {alt[:55]}"
                    logging.info(f"[{st['done'] + 1}/{total}] {vid} @{start:>4}s  {row['artist']} - {row['title']}"
                                 f"   [{row['label']}, {row['released']}]{mark}")
                else:
                    row["stable"] = False
                    logging.info(f"[{st['done'] + 1}/{total}] {vid} @{start:>4}s  no match")
            except Exception as e:
                st["fail"] += 1
                st["streak"] += 1
                # `or [""]` matters: some exceptions carry no message at all
                # (asyncio.TimeoutError is the common one here), and "".splitlines()
                # is [], so indexing [0] crashes the handler itself and takes down
                # the whole run while trying to record a routine failure.
                row["error"] = f"{type(e).__name__}: {(str(e).splitlines() or [''])[0][:200]}"
                logging.error(f"[{st['done'] + 1}/{total}] {vid} @{start}s failed: {row['error']}")

            rows[(vid, start)] = row
            st["done"] += 1

            # Network down, or Shazam finally objecting to the pace: every
            # remaining clip would fail the same way. Stop and keep what we have;
            # errored clips are retried on the next run, so nothing is lost.
            if st["streak"] >= FAILURE_STREAK_LIMIT:
                st["abort"] = True
                write(rows, out_path)
                logging.error(
                    f"{st['streak']} consecutive failures -- stopping early "
                    f"(network down, or too much concurrency?). Re-run to resume; "
                    f"completed clips are already saved."
                )
                return

            if st["done"] % 20 == 0 or st["done"] == total:
                write(rows, out_path)
            if sleep_sec > 0:
                await asyncio.sleep(sleep_sec)

    await asyncio.gather(*(one(vid, start) for vid, start in todo))
    return st["ok"], st["fail"], st["hits"], st["stable"]


def write(rows: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(list(rows.values()), columns=SCHEMA)
    df = df.sort_values(["video_id", "start_sec"])
    df.to_csv(out_path, index=False, encoding="utf-8")


def main(metadata: Path, audio_dir: Path, out_path: Path, ids: str | None,
         limit: int | None, every: int, clip_len: float, max_clips: int | None,
         sleep_sec: float, attempts: int, shift: float, concurrency: int,
         timeout: float) -> int:
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
        f"({clip_len:g}s every {every}s, {attempts} attempt(s) per match, "
        f"{concurrency} at a time, {sleep_sec}s between calls)"
    )
    if not todo:
        logging.info("nothing to do")
        return 0

    t0 = time.time()
    ok, fail, hits, stable_hits = asyncio.run(
        run(todo, paths, clip_len, sleep_sec, out_path, rows, attempts, shift, concurrency, timeout))
    write(rows, out_path)
    logging.info(
        f"done in {time.time() - t0:.0f}s. {ok} recognized, {fail} failed, "
        f"{hits} matched a song of which {stable_hits} stable "
        f"({hits - stable_hits} disagreed across attempts) -> {out_path}"
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
    p.add_argument("--sleep", type=float, default=0.15,
                   help="seconds between calls within a worker (default 0.15; no "
                        "rate-limiting has been observed, the circuit breaker catches it if it starts)")
    p.add_argument("--concurrency", type=int, default=1,
                   help="clips in flight at once (default 1). MEASURED: Shazam allows a short "
                        "burst then throttles sustained overlap. 5 stalled a run to zero "
                        "completions; 3 served 28 clips then timed out on every request until "
                        "the breaker fired. 1 sustains ~1.8s/clip indefinitely.")
    p.add_argument("--timeout", type=float, default=45.0,
                   help="seconds before a single recognition is abandoned (default 45). "
                        "Turns a throttle stall into a countable failure the circuit "
                        "breaker can act on.")
    p.add_argument("--attempts", type=int, default=2,
                   help="time-shifted windows to check each MATCHING clip against; a match "
                        "that does not survive the shift is noise (default 2, 1 disables)")
    p.add_argument("--shift", type=float, default=5.0,
                   help="seconds to slide the window per extra attempt (default 5)")
    args = p.parse_args()
    sys.exit(main(args.metadata, args.audio, args.out, args.ids, args.limit,
                  args.every, args.duration, args.max_clips, args.sleep,
                  args.attempts, args.shift, args.concurrency, args.timeout))
