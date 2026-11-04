"""
Map multi-sketch videos onto the archive: which sketch plays when, and what is unknown
(plan steps 0.6 and M4/M5, docs/superpowers/plans/2026-11-03-extend-archive.md).

For each video in the pool: match its WHOLE audio against an index (scripts/audio_index.py,
up to 40 hits), keep hits whose matched stretch of the video is >= MIN_SPAN_SEC, then
CONFIRM each by sample-level cross-correlation of that stretch against the matched
recording at the reported offset, in 10 s windows with a local lag search: a whole-span
correlation fails on genuine matches once a tiny clock drift accumulates. Density per query second can't be the test
here: one 150 s sketch inside 1,000 s of compilation scores ~1.2/s overall. The
correlation separates same-recording (0.86-0.99, _learnings/ 2026-08-01) from shared
music or stings with different dialogue on top.

Confirmed spans become the timeline; gaps of >= MIN_GAP_SEC are `unknown` spans, the
candidates for sketches the archive doesn't have.

Writes data/compilations/hits_<set>.jsonl (archive index) and hits_<set>_<index>.jsonl
(others), raw engine hits, resume-safe; then timeline_<set>.csv and audit_<set>.csv. Usage:
  uv run --group match python scripts/non_essential/map_compilations.py --set archive
  uv run --group match python scripts/non_essential/map_compilations.py --set pool --index archive candidates
Runtime (measured 2026-11-03): matching ~65 s per pool video (they average ~30 min) per
index, so ~4.5 h per index for the 256-video pool; the confirm step and audit after it are
mostly whole-file decodes, ~12 s per 20 min of query.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
COMP = ROOT / "data" / "compilations"
MIN_SPAN_SEC = 20.0     # long-enough stretches go through the density rules below
# Highlight reels cut sketches into 3-20 s pieces (review: 4fPaXrlVeP8 matched 15 archive
# sketches, almost all under 20 s). A piece of SHORT_MIN_SEC-MIN_SPAN_SEC at >= SHORT_DENSITY
# hashes/s is accepted only if a sample-level correlation of that exact piece confirms it.
# The shared ~2.8 s sting stays below SHORT_MIN_SEC.
SHORT_MIN_SEC = 5.0
SHORT_DENSITY = 8.0
MIN_GAP_SEC = 30.0      # an unmatched stretch at least this long is worth a look
CONFIRM_R = 0.6         # same audio; August measured 0.86-0.99 same vs ~0.01 unrelated
WINDOW_SEC = 10.0       # correlate in windows: long spans drift out of sample alignment
PAD_SEC = 0.5           # per-window lag search
MAX_WINDOWS = 6         # windows per span, spread evenly (bounds the decoding cost)
AGREE = 0.5             # share of windows that must correlate for a span to count
# Hashes per second of the matched stretch. On the archive's own compilations (2026-11-03)
# all 69 confirmed hits scored >= 6.22/s and all 5 rejected ones <= 0.96/s, so only the
# band between is worth the windowed check (decoding costs ~12 s per 20 min of query plus
# ~0.38 s per window; checking everything would take ~5.5 h on the fan pool).
# The audit of that first run (audit_archive.csv) moved the accept line from 4.0 to 6.2:
# 1 of 8 audited accepts below 6.2/s failed the windowed check (4.58/s, a 22 s stretch
# inside another sketch's confirmed span), 0 of 42 at or above it.
ACCEPT_DENSITY = 6.2
REJECT_DENSITY = 1.5
# A hit on a FAN clip (candidates index) means "a standalone upload of this exists" only if
# it covers at least half that clip. Shared intros are identical audio, so correlation can't
# reject them; coverage can (one uploader opens every Kaset clip with the same ~25 s).
CANDIDATE_COVER = 0.5
AUDIT_N = 50            # shortcut decisions re-checked the slow way, per side (seed 509)
SR = 8000

log = logging.getLogger("map_compilations")


def decode(path: Path) -> np.ndarray:
    """Whole file as mono float32 at SR. A 95-minute tape is ~180 MB; decoded once per video."""
    proc = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                          capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed on {path.name}: {proc.stderr.decode(errors='replace')[:300]}")
    return np.frombuffer(proc.stdout, dtype=np.float32)


def decode_span(path: Path, start: float, dur: float) -> np.ndarray:
    """`dur` seconds of `path` from `start`, via ffmpeg's fast input seek (~0.15 s a call)."""
    proc = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(start, 0):.2f}", "-t", f"{dur:.2f}",
                           "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                          capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed on {path.name}: {proc.stderr.decode(errors='replace')[:300]}")
    return np.frombuffer(proc.stdout, dtype=np.float32)


def window_corr(a: np.ndarray, b: np.ndarray) -> float:
    """Best normalised correlation of window `a` against every position in the longer `b`.

    `b` is `a`'s span plus a margin on each side, so this is a local lag search. Each lag
    is normalised by the energy of the part of `b` it overlaps, so it's a true
    correlation coefficient (~1 same recording, ~0 unrelated).
    """
    n, m = len(a), len(b)
    if n < SR or m < n:
        return 0.0
    a = a - a.mean()
    na = np.linalg.norm(a) + 1e-12
    size = 1 << int(np.ceil(np.log2(n + m)))
    c = np.fft.irfft(np.fft.rfft(b, size) * np.conj(np.fft.rfft(a, size)), size)[: m - n + 1]
    e = np.concatenate([[0.0], np.cumsum(b * b)])
    nb = np.sqrt(np.maximum(e[n:] - e[: m - n + 1], 0)) + 1e-12
    return float(np.max(np.abs(c) / (na * nb)))


def span_agreement(q: np.ndarray, ref: Path, q_start: float, q_end: float, offset: float) -> float:
    """Share of WINDOW_SEC windows along the span that correlate >= CONFIRM_R.

    `q` is the whole decoded query (decoded once: queries are the long compilations);
    the ref is read only at each window, by fast seek. `offset` maps query time to ref
    time. (Decoding every ref whole was measured slower: ~2.5 s per file.)
    A single correlation over the whole span fails on genuine matches: a clock drift of
    ~0.002% (measured: lag walking -6 -> -2 ms over 200 s inside Fyc5VWnAMog) puts
    samples out of step long before the end. Windowed, each with its own +-PAD_SEC lag
    search, the same span scored 0.95-0.99 on most windows.
    """
    span = q_end - q_start
    w = min(WINDOW_SEC, span)
    n = max(1, min(MAX_WINDOWS, int(span // WINDOW_SEC)))
    starts = np.linspace(q_start, q_end - w, n) if span > w else [q_start]
    good = 0
    for s in starts:
        a = q[int(s * SR): int((s + w) * SR)].astype(np.float64)
        b = decode_span(ref, s + offset - PAD_SEC, w + 2 * PAD_SEC).astype(np.float64)
        good += window_corr(a, b) >= CONFIRM_R
    return good / len(starts)


def timeline(video_dur: float, spans: list[dict]) -> list[dict]:
    """Confirmed spans in order, with `unknown` rows for every gap >= MIN_GAP_SEC."""
    rows, cursor = [], 0.0
    for s in sorted(spans, key=lambda x: x["start_sec"]):
        if s["start_sec"] - cursor >= MIN_GAP_SEC:
            rows.append({"start_sec": round(cursor, 1), "end_sec": round(s["start_sec"], 1), "match_kind": "unknown"})
        rows.append(s)
        cursor = max(cursor, s["end_sec"])
    if video_dur - cursor >= MIN_GAP_SEC:
        rows.append({"start_sec": round(cursor, 1), "end_sec": round(video_dur, 1), "match_kind": "unknown"})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", choices=["archive", "pool"], required=True,
                    help="archive = the archive's own compilations (audio in data/audio); pool = fan videos")
    ap.add_argument("--index", nargs="+", default=["archive"],
                    help="one or more indexes; hits are merged (M4 uses archive + candidates)")
    args = ap.parse_args()
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(),
                                  logging.FileHandler(ROOT / "logs" / "map_compilations.log", encoding="utf-8")])
    import audio_index as ai

    pool = pd.read_csv(COMP / "pool.csv", dtype={"video_id": str})
    if args.set == "archive":
        want = set(pool.loc[pool.source == "archive", "video_id"])
        files = [p for p in (ROOT / "data" / "audio").iterdir() if ai.video_id_of(p) in want]
    else:
        # The M2 list (in scope, one copy per group). Audio on disk for anything else, such as
        # the No Comment stage show ruled out of scope after its download (Q21), is ignored.
        want = set((COMP / "pool_download_ids.txt").read_text(encoding="utf-8").split())
        # finished audio only: a .part is a download still in progress (or interrupted)
        files = sorted(f for f in (COMP / "audio").iterdir()
                       if f.suffix.lower() in ai.AUDIO_EXT and ai.video_id_of(f) in want)
        missing = want - {ai.video_id_of(f) for f in files}
        if missing:
            log.warning(f"{len(missing)} pool videos have no audio (download failed or not run): {sorted(missing)}")
    t0 = time.time()
    merged: dict[str, dict] = {}
    for index in args.index:
        hits_path = COMP / (f"hits_{args.set}.jsonl" if index == "archive" else f"hits_{args.set}_{index}.jsonl")
        # full matched extents (quantile 0): the default 5% trim left false 30 s gaps between
        # adjacent sketches (5 of the archive's 7 "unknown" gaps were this, review 2026-11-03)
        # The analysis of each video is cached: it is ~85% of a match and the same for every index.
        ai.match(index, files, hits_path, max_hits=40, time_quantile=0.0, hash_cache=COMP / "hashes")
        for line in hits_path.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            r = json.loads(line)
            if r["video_id"] in want:      # rows matched before a video left the set stay out
                merged.setdefault(r["video_id"], {**r, "hits": []})["hits"] += r["hits"]

    paths = {}
    for root in (ROOT / "data" / "audio", ROOT / "data" / "candidates" / "audio"):
        if root.exists():
            paths.update({ai.video_id_of(p): p for p in root.iterdir() if p.suffix.lower() in ai.AUDIO_EXT})
    # Reference lengths, to clip a stretch to where the reference can actually lie.
    ref_dur = pd.read_csv(ROOT / "data" / "youtube_metadata.csv", dtype={"video_id": str}).set_index(
        "video_id")["duration_sec"].to_dict()
    cand_hits = ROOT / "data" / "candidates" / "matches_archive.jsonl"
    if cand_hits.exists():
        for line in cand_hits.read_text(encoding="utf-8").splitlines():
            if line:
                r = json.loads(line)
                ref_dur.setdefault(r["video_id"], r["query_dur"])
    out = []
    shortcut: list[tuple] = []
    rows = list(merged.values())
    t_confirm = time.time()            # the ETA below must not count the matching phase
    for i, r in enumerate(rows, 1):
        vid, qpath = r["video_id"], ROOT / r["query"]
        q = None
        spans = []
        for h in r["hits"]:
            if h["ref"] == vid:
                continue
            # Clip to where the reference can lie at this offset (ref time = query time + offset).
            rd = ref_dur.get(h["ref"])
            if rd is None or rd != rd:
                raise RuntimeError(f"no duration for reference {h['ref']}: can't place its stretch")
            q0 = max(h["q_start"], -h["offset_sec"], 0.0)
            q1 = min(h["q_end"], rd - h["offset_sec"], r["query_dur"])
            span = q1 - q0
            if span < SHORT_MIN_SEC:
                continue
            is_cand = "candidates" in h["ref_path"]
            if is_cand and span < CANDIDATE_COVER * rd:
                log.info(f"{vid}: rejected fan clip {h['ref']} at {q0:.0f}-{q1:.0f} s "
                         f"(covers {span / rd:.0%} of it: a shared intro or a partial overlap)")
                continue
            dens = h["aligned"] / span
            if span < MIN_SPAN_SEC:
                if dens < SHORT_DENSITY:
                    continue
                if q is None:
                    q = decode(qpath)
                piece = decode_span(paths[h["ref"]], q0 + h["offset_sec"] - PAD_SEC, span + 2 * PAD_SEC).astype(np.float64)
                corr = float(window_corr(q[int(q0 * SR): int(q1 * SR)].astype(np.float64), piece) >= CONFIRM_R)
                how = "short_piece"
            elif dens >= ACCEPT_DENSITY:
                corr, how = 1.0, "dense"
                shortcut.append(("accepted", vid, qpath, h["ref"], q0, q1, h["offset_sec"], dens))
            elif dens < REJECT_DENSITY:
                corr, how = 0.0, "sparse"
                shortcut.append(("rejected", vid, qpath, h["ref"], q0, q1, h["offset_sec"], dens))
            else:
                if q is None:
                    q = decode(qpath)
                corr, how = span_agreement(q, paths[h["ref"]], q0, q1, h["offset_sec"]), "windows"
            if corr >= AGREE:
                spans.append({"start_sec": round(q0, 2), "end_sec": round(q1, 2),
                              "match_kind": "candidate" if "candidates" in h["ref_path"] else "archive",
                              "match_video_id": h["ref"], "offset_sec": h["offset_sec"],
                              "aligned": h["aligned"], "span_density": round(dens, 2),
                              "confirmed_by": how, "windows_agree": round(corr, 2) if how == "windows" else ""})
            else:
                log.info(f"{vid}: rejected {h['ref']} at {h['q_start']:.0f}-{h['q_end']:.0f} s "
                         f"({how}: {dens:.2f} hashes/s" + (f", {corr:.0%} of windows agree" if how == "windows" else "")
                         + f", {h['aligned']} hashes)")
        for row in timeline(r["query_dur"], spans):
            out.append({"compilation_id": vid, "duration_sec": r["query_dur"], **row})
        el = time.time() - t_confirm
        log.info(f"[{i}/{len(rows)}] {vid}: {len(spans)} confirmed spans "
                 f"({el:.0f}s into the confirm step, ~{el / i * (len(rows) - i):.0f}s left)")
    # Audit the density shortcut: re-check a seeded sample of its decisions the slow way.
    import random
    rng = random.Random(509)
    audit = []
    picked = []
    for side in ("accepted", "rejected"):
        pool_ = [s for s in shortcut if s[0] == side]
        picked += rng.sample(pool_, min(AUDIT_N, len(pool_)))
    # Group by query and decode each long query ONCE: seeking into a 20-95 min compilation
    # costs ~8 s a call (measured: the first audit took 2.5 h on the archive set this way).
    by_query: dict[Path, list] = {}
    for s in picked:
        by_query.setdefault(s[2], []).append(s)
    for qp, group in by_query.items():
        qa = decode(qp)
        for (decision, cid, _qp, ref, a0, a1, off, dens) in group:
            agree = span_agreement(qa, paths[ref], a0, a1, off)
            audit.append({"decision": decision, "compilation_id": cid, "ref": ref, "start_sec": round(a0, 1),
                          "end_sec": round(a1, 1), "span_density": round(dens, 2), "windows_agree": round(agree, 2),
                          "disagrees": (agree >= AGREE) != (decision == "accepted")})
    if audit:
        a = pd.DataFrame(audit)
        a.to_csv(COMP / f"audit_{args.set}.csv", index=False, encoding="utf-8")
        for side, g in a.groupby("decision"):
            log.info(f"shortcut audit, {side}: {int(g.disagrees.sum())} of {len(g)} disagree with the windowed check")
    df = pd.DataFrame(out)
    dest = COMP / f"timeline_{args.set}.csv"
    df.to_csv(dest, index=False, encoding="utf-8")
    log.info(f"{dest}: {len(df)} rows, {dict(df.match_kind.value_counts())}; {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
