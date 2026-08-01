"""Compute a robust acoustic fingerprint for every file in data/audio/.

Why fingerprints and not metadata: this archive's titles are a template
("Kargin Haghordum sketch NNN (Hayko Mko)"), so string similarity between any
two rows scores ~0.95 on boilerplate alone. Same-title rows turn out to be
*different* sketches (188s vs 88s), and the one duplicate we could confirm by
hand has *different* titles. Duration collides by coincidence in 162 groups.
Only the audio identifies "same recording, uploaded twice".

Method: a Haitsma-Kalker style sub-fingerprint. Decode the first N seconds to
8 kHz mono, take a 2048/1024 STFT, sum power into 32 log-spaced bands over
300-3000 Hz (the speech range), then emit one bit per adjacent band pair:

    bit[n][m] = 1 if (E[n][m] - E[n][m+1]) - (E[n-1][m] - E[n-1][m+1]) > 0

That double difference (across bands, then across time) is what makes this
robust: re-encoding, volume changes and EQ shift band energies but preserve
their *relative* movement, so the bits survive. 31 bits per 128 ms frame,
packed into uint32 so comparison is an XOR plus a popcount.

Only the first N seconds are decoded (`-t` as an ffmpeg *input* option, so it
stops reading rather than decoding all 34 hours and throwing it away).

Resume-safe: video_ids already in the output file are skipped.

Usage:
    uv run python scripts/fingerprint_audio.py
    uv run python scripts/fingerprint_audio.py --seconds 120     # longer, more robust
    uv run python scripts/fingerprint_audio.py --limit 5         # smoke test
    uv run python scripts/fingerprint_audio.py --force           # ignore cache
"""

from __future__ import annotations

import argparse
import logging
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "fingerprint_audio.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

AUDIO_FILENAME = re.compile(r"^(\d{3})_.*?([A-Za-z0-9_-]{11})\.[^.]+$")

# Fingerprint geometry. Changing any of these invalidates existing fingerprints,
# so they are written into the .npz and checked on load.
SAMPLE_RATE = 8000        # speech lives well under 4 kHz; decoding lower is cheaper
N_FFT = 2048              # 256 ms window
HOP = 1024                # 128 ms step -> ~7.8 frames/sec
N_BANDS = 32              # -> 31 bits per frame
BAND_LO_HZ = 300.0
BAND_HI_HZ = 3000.0


def band_edges() -> np.ndarray:
    """FFT bin index for each of the N_BANDS+1 log-spaced band edges."""
    hz = np.logspace(np.log10(BAND_LO_HZ), np.log10(BAND_HI_HZ), N_BANDS + 1)
    bins = np.round(hz / (SAMPLE_RATE / N_FFT)).astype(np.int64)
    if np.any(np.diff(bins) < 1):
        raise ValueError(f"band edges collapse at this FFT size: {bins}")  # loud, not silently merged
    return bins


def decode(path: Path, seconds: int) -> np.ndarray:
    """First `seconds` of `path` as mono float32 at SAMPLE_RATE, via ffmpeg."""
    cmd = [
        "ffmpeg", "-v", "error",
        "-t", str(seconds),          # input option: stop *reading* here
        "-i", str(path),
        "-ac", "1", "-ar", str(SAMPLE_RATE),
        "-f", "f32le", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed on {path.name}: {proc.stderr.decode(errors='replace')[:300]}")
    audio = np.frombuffer(proc.stdout, dtype=np.float32)
    if audio.size < N_FFT * 2:
        raise RuntimeError(f"decoded only {audio.size} samples from {path.name} (too short to fingerprint)")
    return audio


def fingerprint(audio: np.ndarray, edges: np.ndarray, window: np.ndarray) -> np.ndarray:
    """(n_frames-1,) uint32, 31 meaningful bits per frame."""
    n_frames = 1 + (audio.size - N_FFT) // HOP
    frames = np.lib.stride_tricks.sliding_window_view(audio, N_FFT)[:: HOP][:n_frames]
    power = np.abs(np.fft.rfft(frames * window, axis=1)) ** 2

    # reduceat's final group runs to the end of the spectrum; we pass all edges
    # and drop that trailing group so the top band really stops at BAND_HI_HZ.
    energy = np.add.reduceat(power, edges, axis=1)[:, :N_BANDS]

    band_diff = energy[:, :-1] - energy[:, 1:]          # across bands
    bits = (band_diff[1:] - band_diff[:-1]) > 0         # then across time
    weights = (1 << np.arange(N_BANDS - 1, dtype=np.uint32))
    return (bits.astype(np.uint32) * weights).sum(axis=1).astype(np.uint32)


def load_cache(out_path: Path, seconds: int) -> dict[str, np.ndarray]:
    if not out_path.exists():
        return {}
    with np.load(out_path) as z:
        geom = tuple(int(x) for x in z["__geometry__"])
        want = (SAMPLE_RATE, N_FFT, HOP, N_BANDS, seconds)
        if geom != want:
            logging.warning(f"cache geometry {geom} != {want}; recomputing everything")
            return {}
        return {k: z[k] for k in z.files if not k.startswith("__")}


def save(out_path: Path, fps: dict[str, np.ndarray], seconds: int) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    geom = np.array([SAMPLE_RATE, N_FFT, HOP, N_BANDS, seconds], dtype=np.int64)
    np.savez_compressed(out_path, __geometry__=geom, **fps)


def main(audio_dir: Path, out_path: Path, seconds: int, limit: int | None, force: bool) -> int:
    if not audio_dir.exists():
        logging.error(f"audio dir not found: {audio_dir}")
        return 2

    files = {}
    for p in sorted(audio_dir.iterdir()):
        if p.is_file() and (m := AUDIO_FILENAME.match(p.name)):
            files[m.group(2)] = p
    logging.info(f"{len(files)} audio files in {audio_dir}")

    fps = {} if force else load_cache(out_path, seconds)
    todo = [vid for vid in files if vid not in fps]
    if limit is not None:
        todo = todo[:limit]
    logging.info(f"{len(fps)} cached, {len(todo)} to fingerprint (first {seconds}s each)")
    if not todo:
        logging.info("nothing to do")
        return 0

    edges = band_edges()
    window = np.hanning(N_FFT).astype(np.float32)
    failures: list[tuple[str, str]] = []

    for i, vid in enumerate(todo, 1):
        try:
            fps[vid] = fingerprint(decode(files[vid], seconds), edges, window)
        except (RuntimeError, ValueError) as e:
            failures.append((vid, str(e)))
            logging.error(f"[{i}/{len(todo)}] {vid}: {e}")
            continue
        if i % 50 == 0 or i == len(todo):
            logging.info(f"[{i}/{len(todo)}] {vid} -> {len(fps[vid])} frames")
            save(out_path, fps, seconds)  # checkpoint, so a crash doesn't lose the run

    save(out_path, fps, seconds)
    size_mb = out_path.stat().st_size / 1024**2
    logging.info(f"wrote {len(fps)} fingerprints to {out_path} ({size_mb:.1f} MB)")

    if failures:
        logging.error(f"{len(failures)} file(s) failed to fingerprint: {failures}")
        return 1
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--audio", default=Path("data/audio"), type=Path)
    p.add_argument("--out", default=Path("data/audio_fingerprints.npz"), type=Path)
    p.add_argument("--seconds", type=int, default=60, help="how much of each file to fingerprint")
    p.add_argument("--limit", type=int, default=None, help="for smoke testing")
    p.add_argument("--force", action="store_true", help="recompute even if cached")
    args = p.parse_args()
    sys.exit(main(args.audio, args.out, args.seconds, args.limit, args.force))
