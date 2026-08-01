import pandas as pd
import pytest

from scripts.kargin_build.songs import load_songs


def _csv(tmp_path, rows):
    p = tmp_path / "song_matches.csv"
    pd.DataFrame(rows).to_csv(p, index=False)
    return p


BASE = dict(video_id="aaaaaaaaaaa", start_sec=0, matched=True, artist="ABBA",
            title="Dancing Queen", album="Arrival", label="Polar", released="1976.0",
            shazam_url="https://shazam.com/x", verdict="confirmed")


def test_missing_file_is_not_an_error(tmp_path):
    # Song recognition is an optional, partially-complete pass.
    assert load_songs(tmp_path / "nope.csv") == {}


def test_missing_column_fails_loudly(tmp_path):
    p = _csv(tmp_path, [{"video_id": "a", "start_sec": 0}])
    with pytest.raises(ValueError, match="missing required columns"):
        load_songs(p)


def test_keeps_only_confirmed(tmp_path):
    p = _csv(tmp_path, [
        {**BASE, "start_sec": 0},
        {**BASE, "start_sec": 30, "title": "Noise", "verdict": "contradicted"},
        {**BASE, "start_sec": 60, "title": "Unsure", "verdict": "inconclusive"},
        {**BASE, "start_sec": 90, "title": "Nothing", "matched": False, "verdict": "no_match"},
    ])
    songs = load_songs(p)["aaaaaaaaaaa"]
    assert [s["title"] for s in songs] == ["Dancing Queen"]


def test_same_track_collapses_and_keeps_every_offset(tmp_path):
    p = _csv(tmp_path, [{**BASE, "start_sec": 0}, {**BASE, "start_sec": 30}, {**BASE, "start_sec": 90}])
    songs = load_songs(p)["aaaaaaaaaaa"]
    assert len(songs) == 1
    assert songs[0]["at"] == [0, 30, 90]


def test_release_variants_are_one_song(tmp_path):
    # Shazam lists one recording under several entries; without stripping the
    # parenthetical they would render as two different songs.
    p = _csv(tmp_path, [
        {**BASE, "start_sec": 0, "title": "Песенка о медведях (Где-то на белом свете)"},
        {**BASE, "start_sec": 30, "title": "Песенка о медведях (Remastered 2024)"},
    ])
    songs = load_songs(p)["aaaaaaaaaaa"]
    assert len(songs) == 1
    assert songs[0]["at"] == [0, 30]


def test_most_heard_track_comes_first(tmp_path):
    p = _csv(tmp_path, [
        {**BASE, "start_sec": 0, "artist": "One Off", "title": "Sting"},
        {**BASE, "start_sec": 30},
        {**BASE, "start_sec": 60},
    ])
    songs = load_songs(p)["aaaaaaaaaaa"]
    assert songs[0]["title"] == "Dancing Queen"   # 2 hits beats 1
    assert songs[1]["title"] == "Sting"


def test_released_float_is_trimmed_to_a_year(tmp_path):
    songs = load_songs(_csv(tmp_path, [BASE]))["aaaaaaaaaaa"]
    assert songs[0]["released"] == "1976"


def test_videos_without_confirmed_songs_are_absent(tmp_path):
    p = _csv(tmp_path, [{**BASE, "video_id": "bbbbbbbbbbb", "verdict": "contradicted"}])
    assert "bbbbbbbbbbb" not in load_songs(p)
