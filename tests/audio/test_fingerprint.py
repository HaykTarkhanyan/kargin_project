"""Prove the fingerprint actually separates same-recording from different-recording.

The duplicate detection rests entirely on one claim: identical recordings score
near BER 0 and unrelated ones score near 0.5, with nothing in between. These
tests check that on synthetic audio, so a regression in the fingerprint geometry
gets caught without needing the 1.5 GB archive.
"""

import numpy as np
import pytest

from scripts.fingerprint_audio import (
    SAMPLE_RATE, N_FFT, N_BANDS, band_edges, fingerprint,
)
from scripts.detect_duplicates import ber, best_ber

SECONDS = 20
WINDOW = np.hanning(N_FFT).astype(np.float32)
EDGES = band_edges()


def _synth(seed):
    """Speech-ish noise: white noise under a slowly varying amplitude envelope."""
    rng = np.random.default_rng(seed)
    n = SECONDS * SAMPLE_RATE
    noise = rng.standard_normal(n).astype(np.float32)
    t = np.arange(n) / SAMPLE_RATE
    envelope = (0.5 + 0.5 * np.sin(2 * np.pi * 3.0 * t)).astype(np.float32)
    return noise * envelope


def _fp(audio):
    return fingerprint(audio, EDGES, WINDOW)


def test_band_edges_strictly_increasing():
    assert np.all(np.diff(EDGES) >= 1), EDGES
    assert len(EDGES) == N_BANDS + 1


def test_identical_audio_scores_zero():
    a = _synth(509)
    assert ber(_fp(a), _fp(a)) == 0.0


def test_gain_change_is_invisible():
    """A volume difference must not register -- the bits are sign-of-difference,
    and a positive scale factor can't flip a sign."""
    a = _synth(509)
    assert ber(_fp(a), _fp(a * 0.25)) == 0.0
    assert ber(_fp(a), _fp(a * 8.0)) == 0.0


def test_re_encode_noise_stays_well_below_threshold():
    """Lossy re-encoding perturbs band energies; the fingerprint should survive."""
    a = _synth(509)
    rng = np.random.default_rng(510)
    noisy = a + 0.05 * rng.standard_normal(a.size).astype(np.float32) * a.std()
    assert ber(_fp(a), _fp(noisy)) < 0.20


def test_unrelated_audio_scores_near_half():
    """Different recordings must land in the ~0.5 cloud, far from the cutoff."""
    score = ber(_fp(_synth(509)), _fp(_synth(1234)))
    assert 0.40 < score < 0.60, score


def test_best_ber_recovers_a_time_shift():
    """A re-upload with extra leading bumper is the same audio, offset in time."""
    a = _fp(_synth(509))
    shifted = a[20:]
    score, offset = best_ber(a, shifted, max_offset=64)
    assert score == 0.0
    assert offset == 20


def test_best_ber_finds_nothing_in_unrelated_audio():
    """No time shift should be able to rescue two different recordings."""
    score, _ = best_ber(_fp(_synth(509)), _fp(_synth(1234)), max_offset=64)
    assert score > 0.30, score


@pytest.mark.parametrize("seconds", [5, 20])
def test_fingerprint_length_tracks_input(seconds):
    audio = _synth(509)[: seconds * SAMPLE_RATE]
    expected = (1 + (audio.size - N_FFT) // 1024) - 1   # HOP=1024, minus the time-delta frame
    assert _fp(audio).size == expected
