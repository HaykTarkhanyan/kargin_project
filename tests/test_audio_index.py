"""The audio-match engine: id parsing, hit conversion, and an end-to-end offset check.

The end-to-end test needs audfprint2 (the `match` dependency group). It is skipped,
visibly, where that group isn't installed (CI); locally it builds a tiny index from
synthetic audio and checks that a clip cut from the middle of one recording is found
in that recording at the right offset, and that unrelated audio is not.
"""

import wave

import numpy as np
import pytest

from scripts.audio_index import (
    FRAME_SEC, MATCH_DENSITY, audio_files, hit_record, video_id_of,
)


def test_video_id_from_archive_and_candidate_names():
    assert video_id_of("data/audio/042_Kargin_Haghordum_sketch_5_Hayko_Mko_e3ZzwEC5pZ0.webm") == "e3ZzwEC5pZ0"
    assert video_id_of("data/candidates/audio/-TfXo50-YtQ.m4a") == "-TfXo50-YtQ"


def test_a_name_without_an_id_fails_loudly():
    with pytest.raises(ValueError, match="no 11-character video id"):
        video_id_of("notes.txt")


def test_hit_record_converts_frames_to_seconds_and_density():
    h = hit_record("data/audio/001_x_aaaaaaaaaaa.webm", aligned=300, align_frames=100, raw=400,
                   t_min=10, t_max=50, query_dur=60.0)
    assert h["ref"] == "aaaaaaaaaaa"
    assert h["density"] == 5.0
    assert h["offset_sec"] == round(100 * FRAME_SEC, 2)
    assert (h["q_start"], h["q_end"]) == (round(10 * FRAME_SEC, 2), round(50 * FRAME_SEC, 2))


def test_audio_files_filters_and_sorts(tmp_path):
    for n in ("b_bbbbbbbbbbb.webm", "a_aaaaaaaaaaa.m4a", "readme.txt"):
        (tmp_path / n).write_bytes(b"")
    assert [p.name for p in audio_files([tmp_path])] == ["a_aaaaaaaaaaa.m4a", "b_bbbbbbbbbbb.webm"]
    with pytest.raises(FileNotFoundError):
        audio_files([tmp_path / "missing"])


def _write_wav(path, x, sr=11025):
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def _tone_bursts(rng, seconds, sr=11025):
    """Random 0.2-0.5 s tone bursts: spectral peaks a landmark fingerprint can latch onto."""
    x = np.zeros(int(seconds * sr))
    t = 0
    while t < len(x):
        n = int(rng.uniform(0.2, 0.5) * sr)
        f = rng.uniform(300, 3000)
        seg = np.sin(2 * np.pi * f * np.arange(n) / sr) * np.hanning(n)
        x[t:t + n] += seg[: len(x) - t]
        t += n
    return 0.5 * x / np.abs(x).max()


def test_end_to_end_offset_and_rejection(tmp_path, monkeypatch):
    pytest.importorskip("audfprint2")
    import scripts.audio_index as ai

    sr = 11025
    rng = np.random.default_rng(509)
    refs = tmp_path / "refs"
    refs.mkdir()
    sig = {}
    for vid in ("AAAAAAAAAAA", "BBBBBBBBBBB", "CCCCCCCCCCC"):
        sig[vid] = _tone_bursts(rng, 40)
        _write_wav(refs / f"00{len(sig)}_{vid}.wav", sig[vid])
    # Query: 5 s of noise, then 15 s cut from BBBBBBBBBBB starting at 12 s.
    q = np.concatenate([0.05 * rng.standard_normal(5 * sr), sig["BBBBBBBBBBB"][12 * sr:27 * sr]])
    queries = tmp_path / "queries"
    queries.mkdir()
    _write_wav(queries / "QQQQQQQQQQQ.wav", q)
    _write_wav(queries / "NNNNNNNNNNN.wav", _tone_bursts(np.random.default_rng(7), 20))

    monkeypatch.setattr(ai, "INDEX_DIR", tmp_path / "index")
    ai.ingest("t", [refs], new=True)
    out = tmp_path / "hits.jsonl"
    ai.match("t", [queries], out)
    rows = {r["video_id"]: r for r in map(__import__("json").loads, out.read_text().splitlines())}

    top = rows["QQQQQQQQQQQ"]["hits"][0]
    assert top["ref"] == "BBBBBBBBBBB"
    assert top["density"] >= MATCH_DENSITY
    assert abs(top["offset_sec"] - (12 - 5)) < 0.1     # ref time = query time + offset
    assert all(h["density"] < MATCH_DENSITY for h in rows["NNNNNNNNNNN"]["hits"])


def test_audio_files_from_a_list_file(tmp_path):
    a = tmp_path / "x_aaaaaaaaaaa.m4a"
    a.write_bytes(b"")
    lst = tmp_path / "list.txt"
    lst.write_text(f"{a}\n\n", encoding="utf-8")
    assert audio_files([lst], from_list=True) == [a]


def test_hit_cap_grows_with_query_length():
    from scripts.audio_index import max_hits_for
    assert max_hits_for(90) == 10                    # a screening clip keeps the floor
    assert max_hits_for(77 * 60, floor=40) == 462    # the 77-min compilation that saturated at 40


def test_keep_n_keeps_every_usable_hit():
    from scripts.audio_index import keep_n
    assert keep_n([231, 120, 37, 25, 12, 7], cap=3) == 4     # past the cap down to the last >= 20
    assert keep_n([4918, 900, 655, 5, 4], cap=2) == 3       # many strong copies of one clip
    assert keep_n([20, 12, 7], cap=10) == 3                 # the cap still applies when nothing is usable
    assert keep_n([], cap=10) == 0


def test_match_keeps_usable_hits_and_reuses_the_analysis(tmp_path, monkeypatch):
    """match() keeps every hit >= KEEP_HASHES beyond the cap, and with a hash cache a second
    index reuses the query's analysis instead of redoing it."""
    pytest.importorskip("audfprint2")
    import json
    import types
    import scripts.audio_index as ai

    q = tmp_path / "x_aaaaaaaaaaa.m4a"
    q.write_bytes(b"fake audio")
    analysed = []

    class FakeAnalyzer:
        n_hop, target_sr = 256, 11025

        def wavfile2hashes(self, path):
            analysed.append(path)
            return np.array([[t, 7 * t] for t in range(0, 3876, 4)])   # last hash at frame 3872 = ~90 s

    class FakeMatcher:
        def match_hashes(self, ht, hashes):
            al = [100] * 30 + [5] * 200                             # 30 real hits, then noise
            return np.array([(i, a, 0, a, i, 0, 10) for i, a in enumerate(al)])

    fake_ht = types.SimpleNamespace(names=[f"data/audio/{i:03d}_x_{i:011d}.webm" for i in range(230)])
    monkeypatch.setattr(ai, "INDEX_DIR", tmp_path)
    monkeypatch.setattr(ai, "_analyzer", lambda is_match: FakeAnalyzer())
    import audfprint2.cli as cli
    import audfprint2.core.hash_table as hash_table
    monkeypatch.setattr(hash_table, "HashTable", lambda path: fake_ht)
    monkeypatch.setattr(cli, "setup_matcher", lambda **kw: FakeMatcher())
    cache = tmp_path / "hashes"
    for out in (tmp_path / "a.jsonl", tmp_path / "b.jsonl"):        # two indexes, same query
        ai.match("x", [q], out, max_hits=10, hash_cache=cache)
        rows = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines()]
        assert len(rows) == 1 and len(rows[0]["hits"]) == 30         # all 30 real hits, past the cap of 10
        assert abs(rows[0]["query_dur"] - 3872 * 256 / 11025) < 0.01
    assert len(analysed) == 1                                        # the second index used the cache
    q.write_bytes(b"other audio, other size")                       # a changed file is re-analysed
    ai.match("x", [q], tmp_path / "c.jsonl", max_hits=10, hash_cache=cache)
    assert len(analysed) == 2
