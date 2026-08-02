"""Run recognize_songs.py to completion, riding out Shazam's throttle cycles.

Why this exists
---------------
recognize_songs.py is correct but finite: Shazam serves roughly 12 minutes of
work, then throttles, and the circuit breaker stops the run. Resuming is a
manual step, so the sweep only advances when somebody notices it stopped -- one
cooldown went unattended for 2.5 hours. This owns the whole cycle in a single
process: work, detect the stop, wait out the cooldown, resume, repeat.

Throttle detection is by MEASURED PROGRESS, not exit code. A throttled run and a
finished one both exit non-zero or zero for reasons that do not distinguish them,
but a throttled run recognises almost nothing. Progress is counted from
song_matches.csv, which is the same file the resume logic reads, so the
supervisor and the worker can never disagree about what is done.

The backoff is deliberately asymmetric: a productive round resets the wait to the
measured ~20 minute cooldown, while a round that achieved nothing doubles it. A
throttle that is not lifting is a signal to back further off, not to keep
knocking at a fixed interval.

Nothing here is committed to git -- that stays a human decision.

Usage:
    uv run --group songs python scripts/sweep_songs.py
    uv run --group songs python scripts/sweep_songs.py --max-cycles 5
"""
from __future__ import annotations

import argparse
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
        logging.FileHandler(LOG_DIR / "sweep_songs.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

# Measured twice: a probe 7 min after the breaker fired returned 0/3 timeouts,
# at 22 min it returned 3/3 in under a second.
BASE_WAIT_SEC = 20 * 60
MAX_WAIT_SEC = 60 * 60

# Below this, the round accomplished nothing worth counting and we are still
# being throttled. A healthy round does 100-200.
MIN_PROGRESS = 10

REMAINING = re.compile(r"(\d+) clip\(s\) to recognize")


def scanned(csv: Path) -> int:
    if not csv.exists():
        return 0
    return len(pd.read_csv(csv, dtype=str, keep_default_na=False))


def run_once(cmd: list[str]) -> int | None:
    """Run one sweep, streaming its output. Returns clips left, or None if unknown.

    The worker logs to stderr, so it is merged into stdout and echoed here --
    otherwise a multi-hour run would be completely silent.
    """
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
    )
    remaining = None
    try:
        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            m = REMAINING.search(line)
            if m:
                remaining = int(m.group(1))
            # Only surface milestones; per-clip lines already go to the worker's
            # own log file and would bury this one.
            if m or " - ERROR - " in line or "done in" in line or "resume:" in line:
                logging.info(f"  | {line.split(' - ', 2)[-1]}")
    finally:
        proc.wait()
    return remaining


def main(csv: Path, max_cycles: int, base_wait: float, initial_wait: float,
         worker_args: list[str]) -> int:
    cmd = [sys.executable, "scripts/recognize_songs.py"] + worker_args
    logging.info(f"supervising: {' '.join(cmd)}")

    if initial_wait:
        logging.info(f"starting throttled: waiting {initial_wait/60:.0f} min before the first cycle")
        time.sleep(initial_wait)

    wait, dry_streak = base_wait, 0
    for cycle in range(1, max_cycles + 1):
        before = scanned(csv)
        logging.info(f"=== cycle {cycle}/{max_cycles} -- {before} clips already scanned ===")
        t0 = time.time()
        remaining = run_once(cmd)
        after = scanned(csv)
        gained = after - before
        logging.info(f"cycle {cycle}: +{gained} clips in {time.time()-t0:.0f}s "
                     f"(total {after}, {remaining if remaining is not None else '?'} were queued)")

        if remaining == 0:
            logging.info("nothing left to recognize -- sweep complete")
            return 0
        if remaining is None:
            # The worker never printed its work-list line, so it died before
            # starting. Loud, because it means the command itself is broken.
            logging.error("worker did not report a work list -- aborting rather than "
                          "looping on a broken command")
            return 1

        if gained >= MIN_PROGRESS:
            dry_streak, wait = 0, base_wait
            logging.info(f"productive round; waiting {wait/60:.0f} min for the cooldown")
        else:
            # Doubling is driven by CONSECUTIVE dry rounds, not by the previous
            # wait. The first dry round still gets the plain measured cooldown --
            # one unproductive cycle is normal and does not justify 40 minutes.
            dry_streak += 1
            wait = min(base_wait * 2 ** (dry_streak - 1), MAX_WAIT_SEC)
            logging.warning(f"only +{gained} clips -- still throttled "
                            f"(dry streak {dry_streak}). backing off to {wait/60:.0f} min")

        if cycle < max_cycles:
            time.sleep(wait)

    logging.warning(f"hit --max-cycles ({max_cycles}) with work outstanding. "
                    f"Re-run to continue; nothing is lost.")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default=Path("data/song_matches.csv"), type=Path,
                   help="the worker's output CSV, used to measure progress")
    p.add_argument("--max-cycles", type=int, default=20,
                   help="safety stop so a misbehaving loop cannot run forever (default 20)")
    p.add_argument("--wait-minutes", type=float, default=BASE_WAIT_SEC / 60,
                   help="cooldown after a productive round (default 20, measured)")
    p.add_argument("--initial-wait-minutes", type=float, default=0,
                   help="wait before the FIRST cycle. Use when starting while already "
                        "throttled, so cycle 1 is not spent proving what we know.")
    a, worker_args = p.parse_known_args()

    if not worker_args:
        # The settings that survive: concurrency 1 and sleep 0.5 are measured, and
        # the 4-failure breaker keeps a throttled round from burning 15 minutes.
        worker_args = [
            "--metadata", "data/youtube_metadata.csv", "--every", "30",
            "--concurrency", "1", "--sleep", "0.5", "--attempts", "2",
            "--shift", "5", "--max-consecutive-failures", "4",
        ]
    sys.exit(main(a.out, a.max_cycles, a.wait_minutes * 60,
                  a.initial_wait_minutes * 60, worker_args))
