"""The A4 verdict rules: one stretch of audio is one sketch, however many recordings hold it."""

from scripts.non_essential.match_candidates import UnionFind, distinct_stretches, overlaps


def h(ref, start, end, dens=5.0):
    return {"ref": ref, "q_start": start, "q_end": end, "density": dens}


def test_a_sketch_and_the_compilation_containing_it_are_one_stretch():
    groups = distinct_stretches([h("SKETCH", 2, 84), h("COMPILATION", 5, 80, dens=4.0)])
    assert len(groups) == 1
    assert groups[0][0]["ref"] == "SKETCH"          # densest first


def test_two_sketches_back_to_back_are_two_stretches():
    groups = distinct_stretches([h("FIRST", 0, 40), h("SECOND", 45, 88)])
    assert sorted(g[0]["ref"] for g in groups) == ["FIRST", "SECOND"]


def test_a_short_shared_sting_does_not_merge_two_stretches():
    # A 3 s overlap against a 40 s span is under half the shorter span: still separate.
    assert not overlaps(h("A", 0, 40), h("B", 37, 80))
    assert overlaps(h("A", 0, 40), h("B", 10, 80))


def test_union_find_clusters_copies_transitively():
    uf = UnionFind()
    uf.union("c", "b")
    uf.union("b", "a")
    uf.find("z")
    assert uf.find("c") == uf.find("a") == "a"
    assert uf.find("z") == "z"


def test_compilation_timeline_marks_long_gaps_unknown():
    from scripts.non_essential.map_compilations import MIN_GAP_SEC, timeline
    spans = [{"start_sec": 40.0, "end_sec": 200.0, "match_kind": "archive"},
             {"start_sec": 210.0, "end_sec": 400.0, "match_kind": "archive"}]
    rows = timeline(600.0, spans)
    kinds = [(r["match_kind"], r["start_sec"], r["end_sec"]) for r in rows]
    assert kinds[0] == ("unknown", 0.0, 40.0)            # 40 s gap at the start
    assert ("unknown", 400.0, 600.0) in kinds             # 200 s left at the end
    assert len([k for k in kinds if k[0] == "unknown"]) == 2   # the 10 s gap stays a gap
    assert MIN_GAP_SEC == 30.0


def test_canonical_order_follows_q8():
    from scripts.non_essential.match_candidates import canonical_order
    base = {"status": "ok", "source": "fan", "definition": "sd", "channel_created": "20150101",
            "channel_videos": 10, "upload_date": "20200101"}
    members = [
        {**base, "video_id": "blocked_hd_", "status": "fails_hard_requirements", "definition": "hd"},
        {**base, "video_id": "fan_sd_____"},
        {**base, "video_id": "fan_hd_new_", "definition": "hd", "channel_created": "20220101"},
        {**base, "video_id": "fan_hd_old_", "definition": "hd", "channel_created": "20120101"},
        {**base, "video_id": "kargintv_sd", "source": "kargintv"},
    ]
    order = [m["video_id"] for m in canonical_order(members)]
    assert order == ["kargintv_sd", "fan_hd_old_", "fan_hd_new_", "fan_sd_____", "blocked_hd_"]


def test_window_corr_survives_clock_drift_that_breaks_a_whole_span_correlation():
    """The measured case: a copy ~0.002% off clock (lag -6 -> -2 ms over 200 s in Fyc5VWnAMog)."""
    import numpy as np
    from scripts.non_essential.map_compilations import SR, window_corr
    rng = np.random.default_rng(509)
    # Smoothed noise: short-range structure, like real audio at 8 kHz.
    x = np.convolve(rng.standard_normal(SR * 300), np.ones(8) / 8, mode="same")
    t = np.arange(len(x)) * 1.00002                 # 0.002% fast: 48 samples behind after 300 s
    y = np.interp(t, np.arange(len(x)), x)[: len(x) - 200]
    pad = SR // 2
    # One correlation over the whole 290 s span, searched +-0.5 s: drift smears it.
    whole = window_corr(y[: SR * 290], x[: SR * 290 + 2 * pad])
    # A 10 s window near the end, searched locally: lines up despite the drift.
    late = window_corr(y[SR * 270: SR * 280], x[SR * 270 - pad: SR * 280 + pad])
    assert late > 0.9
    assert whole < 0.6
    assert window_corr(rng.standard_normal(SR * 10), x[: SR * 11]) < 0.1   # unrelated audio


def test_a_shared_intro_is_not_a_copy_link():
    from scripts.non_essential.match_candidates import is_copy_link
    intro = {"density": 3.1, "q_start": 0.2, "q_end": 24.9}     # the uploader's ~25 s opener
    copy = {"density": 7.4, "q_start": 2.0, "q_end": 73.0}      # the real copy pair
    assert not is_copy_link(intro, 90.0)
    assert is_copy_link(copy, 90.0)
    assert not is_copy_link({**copy, "density": 1.0}, 90.0)     # long but too sparse


def test_a_jingle_is_not_a_have():
    from scripts.non_essential.match_candidates import is_have_hit
    jingle = {"density": 2.08, "q_start": 1.46, "q_end": 17.97}   # U39YRsOOw2E's 16.5 s opener
    body = {"density": 5.0, "q_start": 3.0, "q_end": 70.0}
    assert not is_have_hit(jingle, 90.0)
    assert is_have_hit(body, 90.0)
    assert is_have_hit({"density": 4.0, "q_start": 2.0, "q_end": 40.0}, 60.0)   # a 60 s short, 38 s matched


def test_only_permanent_failures_hide_a_candidate():
    from scripts.non_essential.match_candidates import is_permanent_failure
    assert is_permanent_failure("ERROR: [youtube] x: This video is not available")
    assert is_permanent_failure("ERROR: [youtube] x: Private video")
    assert is_permanent_failure("ERROR: [youtube] x: Please sign in. Use --cookies-from-browser")
    assert not is_permanent_failure("ERROR: ffmpeg exited with code 1")
    assert not is_permanent_failure("ERROR: unable to download video data: HTTP Error 403: Forbidden")


def test_archive_duplicates_collapse_to_one_sketch():
    import pandas as pd
    from scripts.non_essential.match_candidates import duplicate_canon
    k = pd.DataFrame({"id": ["010", "020", "030"],
                      "duplicate_of": ["https://youtu.be/BBBBBBBBBBB", "https://www.youtube.com/watch?v=AAAAAAAAAAA", ""]},
                     index=["AAAAAAAAAAA", "BBBBBBBBBBB", "CCCCCCCCCCC"])
    c = duplicate_canon(k)
    assert c["AAAAAAAAAAA"] == c["BBBBBBBBBBB"] == "AAAAAAAAAAA"   # lower id wins
    assert c["CCCCCCCCCCC"] == "CCCCCCCCCCC"


def test_gate_sample_only_grows():
    import pandas as pd
    from scripts.non_essential.gate_unclear import sample
    c = pd.DataFrame({"video_id": [f"v{i:010d}" for i in range(30)], "series": "unclear",
                      "channel_id": "UC1", "channel_title": "Big"})
    first = sample(c, [])
    assert len(first) == 16                                   # 30 unmarked titles -> 16 samples
    again = sample(c, first)
    assert again == first                                     # same sample, nothing re-picked
    more = sample(pd.concat([c, pd.DataFrame({"video_id": [f"w{i:010d}" for i in range(80)], "series": "unclear",
                                              "channel_id": "UC1", "channel_title": "Big"})]), first)
    assert more[:16] == first and len(more) == 24             # channel grew past 100 -> topped up to 24


def test_a_montage_of_one_sketch_matches_but_a_repeated_jingle_does_not():
    from scripts.non_essential.match_candidates import qualifies, sketch_evidence
    # Five 12 s pieces of the same sketch, each from a different part of it (a montage short).
    montage = [{"ref": "S", "aligned": 40, "q_start": 12.0 * i, "q_end": 12.0 * i + 12, "offset_sec": 30.0 * i}
               for i in range(5)]
    ev = sketch_evidence(montage, 60.0, {})["S"]
    assert ev["score"] >= 2.0 and qualifies(ev, 60.0)            # 200 hashes / 60 s, 60 s of the sketch
    # The same 16 s opener matched twice: lots of hashes, but only 16 s of the sketch.
    jingle = [{"ref": "J", "aligned": 100, "q_start": 1.0, "q_end": 17.0, "offset_sec": 0.0},
              {"ref": "J", "aligned": 90, "q_start": 59.0, "q_end": 75.0, "offset_sec": -58.0}]
    ev = sketch_evidence(jingle, 90.0, {})["J"]
    assert ev["score"] >= 2.0 and not qualifies(ev, 90.0)       # covers 16 s < 27 s
    # Duplicates in the archive pool their evidence under one id.
    split = [{"ref": "A", "aligned": 100, "q_start": 0.0, "q_end": 30.0, "offset_sec": 0.0},
             {"ref": "B", "aligned": 100, "q_start": 30.0, "q_end": 60.0, "offset_sec": 0.0}]
    assert set(sketch_evidence(split, 90.0, {"B": "A"})) == {"A"}
