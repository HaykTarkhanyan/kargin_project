"""Find videos that share audio, and say what kind of sharing it is.

Reads data/audio_fingerprints.npz (see fingerprint_audio.py) and writes a
reviewable report to data/duplicates.csv. It does NOT touch kargin_eng.csv --
annotate_kargin_csv.py does that, so you can eyeball the report first.

Why audio and not metadata: every title here is the same template
("Kargin Haghordum sketch NNN (Hayko Mko)"), so string similarity between any
two rows scores ~0.95 on boilerplate alone. Rows that share a title turn out to
be *different* sketches (188s vs 88s), and the one duplicate confirmable by hand
has *different* titles. Duration collides by coincidence in 162 groups. Only the
audio identifies "same recording".

Three stages, cheap to expensive:

  1. SCREEN (all 246k pairs, vectorized). Bit error rate between fingerprints:
     XOR, popcount, divide. Unrelated speech sits at BER ~0.49; anything sharing
     audio falls well below. Keeps a generous shortlist.

  2. ALIGN (shortlist). Re-score over a fine grid of frame offsets, since a
     re-upload may carry a different amount of leading bumper.

  3. CONFIRM (shortlist). Decode both files and cross-correlate at *sample*
     resolution. This stage exists because BER is frame-quantized: at a 128 ms
     hop, a pair misaligned by a fraction of a frame smears across STFT windows
     and scores 0.21-0.33 despite being identical audio. Measured on this
     archive, correlation separates cleanly -- real matches 0.86-0.99, unrelated
     0.010-0.015 -- so BER is only ever a shortlist and correlation is the
     verdict.

Two relations come out, distinguished by duration, because a 877s upload that
opens with a 268s sketch is a compilation, not a duplicate:

  duplicate  same recording uploaded twice     (correlated, near-equal length)
  contains   longer video includes the shorter (correlated, lengths differ)
  partial    correlated but weakly -- review    (overlap outside the window?)

COVERAGE LIMIT: fingerprints cover only the first N seconds of each file, so
this finds pairs that overlap near the *start* of both. A compilation that
includes a sketch eight minutes in will not be found. Detecting that needs
full-length fingerprints and a sliding search.

Usage:
    uv run python scripts/detect_duplicates.py
    uv run python scripts/detect_duplicates.py --no-confirm      # skip decoding
    uv run python scripts/detect_duplicates.py --report-only
"""

from __future__ import annotations

import argparse
import logging
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "detect_duplicates.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

VIDEO_ID_FROM_URL = re.compile(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})")
AUDIO_FILENAME = re.compile(r"^(\d{3})_.*?([A-Za-z0-9_-]{11})\.[^.]+$")

BITS_PER_FRAME = 31          # must match fingerprint_audio.N_BANDS - 1
SCREEN_FRAMES = 128          # ~16 s prefix for the cheap pass
SCREEN_OFFSETS = (-32, -16, -8, 0, 8, 16, 32)
SCREEN_BER = 0.44            # deliberately loose; stage 3 does the judging
SHORTLIST_BER = 0.40
FINE_OFFSET = 64             # +/- ~8 s, step 1
DURATION_TOL_SEC = 5.0       # pairs this close in length always reach stage 2

XCORR_SECONDS = 90           # decode this much per file for the confirm stage
XCORR_SR = 8000
CONFIRM_R = 0.70             # at or above: definitely the same audio
PARTIAL_R = 0.15             # below: reject as a fingerprint false positive
SAME_LENGTH_TOL_SEC = 10.0   # within this => duplicate, beyond => contains


def ber(a: np.ndarray, b: np.ndarray) -> float:
    """Bit error rate between two equal-length uint32 fingerprint arrays."""
    if a.size == 0:
        return 1.0
    return int(np.bitwise_count(a ^ b).sum()) / (a.size * BITS_PER_FRAME)


def best_ber(a: np.ndarray, b: np.ndarray, max_offset: int) -> tuple[float, int]:
    """Lowest BER over frame shifts of b relative to a, and the winning offset."""
    best, best_off = 1.0, 0
    for off in range(-max_offset, max_offset + 1):
        ai, bi = (off, 0) if off >= 0 else (0, -off)
        n = min(a.size - ai, b.size - bi)
        if n < 32:
            continue
        score = ber(a[ai:ai + n], b[bi:bi + n])
        if score < best:
            best, best_off = score, off
    return best, best_off


def screen(fp: np.ndarray, block: int = 32) -> set[tuple[int, int]]:
    """Index pairs worth a closer look, from the cheap prefix pass.

    Compares in row blocks so the intermediate (block, n, frames) array stays
    small instead of materializing n x n x frames all at once.
    """
    n = fp.shape[0]
    keep: set[tuple[int, int]] = set()
    for off in SCREEN_OFFSETS:
        ai, bi = (off, 0) if off >= 0 else (0, -off)
        width = SCREEN_FRAMES - abs(off)
        a_win, b_win = fp[:, ai:ai + width], fp[:, bi:bi + width]
        denom = width * BITS_PER_FRAME
        for start in range(0, n, block):
            stop = min(start + block, n)
            diff = np.bitwise_count(a_win[start:stop, None, :] ^ b_win[None, :, :]).sum(axis=2)
            rows, cols = np.nonzero(diff / denom < SCREEN_BER)
            rows = rows + start
            hit = rows < cols          # upper triangle; both offset signs are searched
            keep.update(zip(rows[hit].tolist(), cols[hit].tolist()))
    return keep


def decode(path: Path, seconds: int) -> np.ndarray:
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-t", str(seconds), "-i", str(path),
         "-ac", "1", "-ar", str(XCORR_SR), "-f", "f32le", "-"],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed on {path.name}: {proc.stderr.decode(errors='replace')[:300]}")
    return np.frombuffer(proc.stdout, dtype=np.float32).astype(np.float64)


def xcorr_peak(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """Peak normalized cross-correlation and its lag in seconds, via FFT.

    Both signals are mean-removed and unit-normalized, so the peak is a true
    correlation coefficient: ~1 for the same recording regardless of volume or
    encoder, ~0.01 for unrelated speech.
    """
    a = a - a.mean()
    b = b - b.mean()
    a = a / (np.linalg.norm(a) + 1e-12)
    b = b / (np.linalg.norm(b) + 1e-12)
    n = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    c = np.fft.irfft(np.fft.rfft(a, n) * np.conj(np.fft.rfft(b, n)), n)
    c = np.abs(np.concatenate([c[-(len(b) - 1):], c[:len(a)]]))
    i = int(np.argmax(c))
    return float(c[i]), (i - (len(b) - 1)) / XCORR_SR


def overlap_fraction(a: np.ndarray, b: np.ndarray, lag_sec: float, window_sec: int = 10) -> float:
    """Share of the aligned span where the two signals actually match locally.

    A single global correlation cannot tell "uniformly degraded copy" from
    "identical for 80% and unrelated for the rest" -- both land mid-range. This
    walks the aligned overlap in windows and reports what fraction of them
    correlate, which is what makes a `partial` verdict interpretable.
    """
    off = int(round(lag_sec * XCORR_SR))
    ai, bi = (off, 0) if off >= 0 else (0, -off)
    n = min(len(a) - ai, len(b) - bi)
    w = window_sec * XCORR_SR
    if n < w:
        return 0.0
    hits = total = 0
    for s in range(0, n - w + 1, w):
        pa, pb = a[ai + s:ai + s + w], b[bi + s:bi + s + w]
        pa, pb = pa - pa.mean(), pb - pb.mean()
        denom = np.linalg.norm(pa) * np.linalg.norm(pb) + 1e-12
        hits += float(np.dot(pa, pb) / denom) > 0.5
        total += 1
    return hits / total if total else 0.0


def classify(r: float, dur_a: float, dur_b: float) -> str:
    if r < PARTIAL_R:
        return "rejected"
    if r < CONFIRM_R:
        return "partial"
    if abs(dur_a - dur_b) <= SAME_LENGTH_TOL_SEC:
        return "duplicate"
    return "contains"


def audio_paths(audio_dir: Path) -> dict[str, Path]:
    return {
        m.group(2): p
        for p in sorted(audio_dir.iterdir())
        if p.is_file() and (m := AUDIO_FILENAME.match(p.name))
    }


def load_context(csv_path: Path, metadata_path: Path) -> pd.DataFrame:
    k = pd.read_csv(csv_path)
    k["video_id"] = k["links"].map(
        lambda u: m.group(1) if isinstance(u, str) and (m := VIDEO_ID_FROM_URL.search(u)) else None
    )
    if k["video_id"].isna().any():
        raise ValueError(f"{k['video_id'].isna().sum()} rows have no parseable video_id")
    meta = pd.read_csv(metadata_path)[["video_id", "title", "duration_sec", "view_count", "upload_date"]]
    if meta["video_id"].duplicated().any():
        raise ValueError("metadata CSV has duplicate video_ids; the merge would fan out rows")
    return k[["video_id", "links", "titles"]].merge(meta, on="video_id", how="left")


def main(fp_path: Path, csv_path: Path, metadata_path: Path, audio_dir: Path,
         out_path: Path, confirm: bool, report_only: bool) -> int:
    if not fp_path.exists():
        logging.error(f"fingerprints not found: {fp_path} -- run scripts/fingerprint_audio.py first")
        return 2

    with np.load(fp_path) as z:
        fps = {k: z[k] for k in z.files if not k.startswith("__")}
    ids = sorted(fps)
    logging.info(f"{len(ids)} fingerprints, {min(fps[i].size for i in ids)}-{max(fps[i].size for i in ids)} frames each")

    ctx = load_context(csv_path, metadata_path).set_index("video_id")
    if missing := [v for v in ctx.index if v not in fps]:
        logging.error(f"{len(missing)} video(s) in the CSV have no fingerprint: {missing[:10]}")
        return 1
    if short := [v for v in ids if fps[v].size < SCREEN_FRAMES]:
        logging.warning(f"{len(short)} fingerprint(s) shorter than the {SCREEN_FRAMES}-frame screen: {short}")

    # --- stage 1: cheap prefix screen over all pairs ---
    screen_fp = np.stack([
        np.pad(fps[v][:SCREEN_FRAMES], (0, max(0, SCREEN_FRAMES - fps[v].size)), constant_values=0)
        for v in ids
    ])
    pairs = screen(screen_fp)
    total_pairs = len(ids) * (len(ids) - 1) // 2
    logging.info(f"stage 1: {len(pairs)} of {total_pairs} pairs survive the prefix screen")

    # Same-length pairs bypass the screen: that is where duplicates live, and a
    # sub-frame misalignment can push a real one above the screen threshold.
    dur = ctx["duration_sec"].reindex(ids).to_numpy(dtype=float)
    order = np.argsort(dur)
    forced = 0
    for a in range(len(order)):
        for b in range(a + 1, len(order)):
            i, j = int(order[a]), int(order[b])
            if dur[j] - dur[i] > DURATION_TOL_SEC:
                break
            key = (min(i, j), max(i, j))
            if key not in pairs:
                pairs.add(key)
                forced += 1
    logging.info(f"stage 1b: +{forced} duration-compatible pairs forced in ({len(pairs)} total)")

    # --- stage 2: fine frame-offset search ---
    scored = [(ids[i], ids[j], *best_ber(fps[ids[i]], fps[ids[j]], FINE_OFFSET)) for i, j in sorted(pairs)]
    scores = np.array([s for _, _, s, _ in scored]) if scored else np.array([1.0])
    logging.info(
        f"stage 2: scored {len(scored)} pairs. BER min={scores.min():.3f} "
        f"p1={np.percentile(scores, 1):.3f} p50={np.percentile(scores, 50):.3f}"
    )
    shortlist = [x for x in scored if x[2] <= SHORTLIST_BER]
    logging.info(f"stage 2: {len(shortlist)} pair(s) below BER {SHORTLIST_BER}")
    if not shortlist:
        logging.info("no shared-audio pairs found")

    # --- stage 3: sample-resolution confirmation ---
    paths = audio_paths(audio_dir)
    cache: dict[str, np.ndarray] = {}
    rows = []
    for a, b, score, off in sorted(shortlist, key=lambda x: x[2]):
        ra, rb = ctx.loc[a], ctx.loc[b]
        if confirm:
            for v in (a, b):
                if v not in cache:
                    cache[v] = decode(paths[v], XCORR_SECONDS)
            r, lag = xcorr_peak(cache[a], cache[b])
            overlap = overlap_fraction(cache[a], cache[b], lag)
            verdict = classify(r, ra["duration_sec"], rb["duration_sec"])
        else:
            r, lag, overlap = float("nan"), off * 1024 / XCORR_SR, float("nan")
            verdict = classify(1.0, ra["duration_sec"], rb["duration_sec"])

        # For `contains` the shorter clip is the original sketch; for a true
        # duplicate the most-viewed upload is the one worth linking to.
        va = 0.0 if pd.isna(ra["view_count"]) else float(ra["view_count"])
        vb = 0.0 if pd.isna(rb["view_count"]) else float(rb["view_count"])
        if verdict == "contains":
            longer = a if ra["duration_sec"] >= rb["duration_sec"] else b
            shorter = b if longer == a else a
            canonical = shorter
        else:
            canonical = a if va >= vb else b
            longer = shorter = ""

        rows.append({
            "verdict": verdict, "corr": round(r, 4), "overlap_pct": round(overlap * 100, 1),
            "lag_sec": round(lag, 3), "ber": round(score, 4), "offset_frames": off,
            "video_id_a": a, "video_id_b": b, "canonical": canonical,
            "compilation": longer, "included_sketch": shorter,
            "url_a": ra["links"], "url_b": rb["links"],
            "title_a": ra["titles"], "title_b": rb["titles"],
            "duration_a": ra["duration_sec"], "duration_b": rb["duration_sec"],
            "views_a": va, "views_b": vb,
            "upload_a": ra["upload_date"], "upload_b": rb["upload_date"],
        })

    counts = pd.Series([r["verdict"] for r in rows]).value_counts().to_dict() if rows else {}
    logging.info(f"stage 3: {counts}")
    for r in sorted(rows, key=lambda x: (x["verdict"], -x["corr"] if x["corr"] == x["corr"] else 0)):
        logging.info(
            f"  [{r['verdict']}] corr={r['corr']:.3f} overlap={r['overlap_pct']:.0f}% "
            f"lag={r['lag_sec']:+.3f}s ber={r['ber']:.3f}  "
            f"{r['video_id_a']} ({r['duration_a']:.0f}s, {r['views_a']:,.0f}v) <-> "
            f"{r['video_id_b']} ({r['duration_b']:.0f}s, {r['views_b']:,.0f}v)"
        )
        logging.info(f"      {r['title_a']!r} <-> {r['title_b']!r}")

    if report_only:
        logging.info("--report-only: not writing the CSV")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=[
        "verdict", "corr", "overlap_pct", "lag_sec", "ber", "offset_frames",
        "video_id_a", "video_id_b", "canonical", "compilation", "included_sketch",
        "url_a", "url_b", "title_a", "title_b",
        "duration_a", "duration_b", "views_a", "views_b", "upload_a", "upload_b",
    ]).to_csv(out_path, index=False, encoding="utf-8")
    logging.info(f"wrote {len(rows)} row(s) to {out_path}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fingerprints", default=Path("data/audio_fingerprints.npz"), type=Path)
    p.add_argument("--csv", default=Path("kargin_eng.csv"), type=Path)
    p.add_argument("--metadata", default=Path("data/youtube_metadata.csv"), type=Path)
    p.add_argument("--audio", default=Path("data/audio"), type=Path)
    p.add_argument("--out", default=Path("data/duplicates.csv"), type=Path)
    p.add_argument("--no-confirm", dest="confirm", action="store_false",
                   help="skip stage 3 (no decoding); trusts BER alone, which is NOT reliable")
    p.add_argument("--report-only", action="store_true", help="log findings without writing the CSV")
    args = p.parse_args()
    sys.exit(main(args.fingerprints, args.csv, args.metadata, args.audio,
                  args.out, args.confirm, args.report_only))
