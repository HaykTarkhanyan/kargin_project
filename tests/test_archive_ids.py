"""The file-number prefix must come from the `id` column, never from row position.

The downloaders used to number a video by its position among the PUBLIC rows of
data/youtube_metadata.csv, so one archive video turning unlisted would shift the
prefix of every later download onto the wrong number (DECISIONS #19, Q19).
"""

import pandas as pd
import pytest

from scripts.archive_ids import load_seq_of


def _csv(tmp_path, rows):
    p = tmp_path / "kargin_eng.csv"
    pd.DataFrame(rows, columns=["id", "titles", "video_id"]).to_csv(p, index=False)
    return p


def test_numbers_come_from_id_not_row_order(tmp_path):
    p = _csv(tmp_path, [("003", "c", "ccccccccccc"), ("001", "a", "aaaaaaaaaaa"), ("002", "b", "bbbbbbbbbbb")])
    assert load_seq_of(p, ["aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc"]) == {
        "aaaaaaaaaaa": 1, "bbbbbbbbbbb": 2, "ccccccccccc": 3}


def test_a_filtered_out_video_does_not_shift_later_numbers(tmp_path):
    # "bbb" went unlisted and is no longer requested; "ccc" must keep 3, not become 2.
    p = _csv(tmp_path, [("001", "a", "aaaaaaaaaaa"), ("002", "b", "bbbbbbbbbbb"), ("003", "c", "ccccccccccc")])
    assert load_seq_of(p, ["aaaaaaaaaaa", "ccccccccccc"]) == {"aaaaaaaaaaa": 1, "ccccccccccc": 3}


def test_leading_zeros_survive(tmp_path):
    p = _csv(tmp_path, [("042", "x", "xxxxxxxxxxx")])
    assert load_seq_of(p, ["xxxxxxxxxxx"]) == {"xxxxxxxxxxx": 42}


def test_a_video_without_a_row_fails_loudly(tmp_path):
    p = _csv(tmp_path, [("001", "a", "aaaaaaaaaaa")])
    with pytest.raises(ValueError, match="no row in"):
        load_seq_of(p, ["aaaaaaaaaaa", "zzzzzzzzzzz"])


def test_duplicate_ids_fail_loudly(tmp_path):
    p = _csv(tmp_path, [("001", "a", "aaaaaaaaaaa"), ("001", "b", "bbbbbbbbbbb")])
    with pytest.raises(ValueError, match="duplicate id"):
        load_seq_of(p, ["aaaaaaaaaaa"])


def test_a_non_numeric_id_fails_loudly(tmp_path):
    p = _csv(tmp_path, [("x01", "a", "aaaaaaaaaaa")])
    with pytest.raises(ValueError, match="not a number"):
        load_seq_of(p, ["aaaaaaaaaaa"])


def test_the_real_archive_matches_metadata_row_order():
    """Today id == row position in youtube_metadata.csv for all 702, so the switch moves nothing."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    meta = pd.read_csv(root / "data" / "youtube_metadata.csv", dtype={"video_id": str})
    ids = meta["video_id"].tolist()
    assert load_seq_of(root / "kargin_eng.csv", ids) == {v: i for i, v in enumerate(ids, 1)}


def test_a_video_on_two_rows_fails_loudly(tmp_path):
    p = _csv(tmp_path, [("001", "a", "aaaaaaaaaaa"), ("002", "a again", "aaaaaaaaaaa")])
    with pytest.raises(ValueError, match="more than one row"):
        load_seq_of(p, ["aaaaaaaaaaa"])
