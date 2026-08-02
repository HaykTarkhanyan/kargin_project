import pandas as pd
import pytest

from scripts.kargin_review.store import EDITABLE_FIELDS, clean, load, plan, record

VID = "aaaaaaaaaaa"


@pytest.fixture
def paths(tmp_path):
    src = tmp_path / "kargin_eng.csv"
    pd.DataFrame([
        {"id": "001", "video_id": VID, "links": "https://youtu.be/" + VID,
         "titles": "sketch 1", "text": "բարև", "text_common": "", "main_actors": "Հայկո",
         "main_actors_count": "1", "roles_names": "", "location": "Տուն",
         "lighting": "", "languages": "հայերեն", "done": "1.0", "duplicate_of": ""},
        {"id": "002", "video_id": "bbbbbbbbbbb", "links": "", "titles": "sketch 2",
         "text": "ոնց ես", "text_common": "", "main_actors": "", "main_actors_count": "",
         "roles_names": "", "location": "", "lighting": "", "languages": "",
         "done": "", "duplicate_of": ""},
    ]).to_csv(src, index=False)
    return {"src": src, "corr": tmp_path / "corrections.csv", "bak": tmp_path / "backups"}


def test_rejects_a_field_that_is_not_editable(paths):
    # video_id / links / duplicate_of are keys or derived: editing them would
    # desynchronise the CSV from the audio files and the site payload.
    # `titles` is YouTube's, not curation output — deliberately not editable.
    for field in ("video_id", "links", "duplicate_of", "id", "titles", "nonsense"):
        assert field not in EDITABLE_FIELDS
        with pytest.raises(ValueError, match="not editable"):
            record(paths["corr"], paths["bak"], VID, field, "x", "y")


def test_records_a_change_and_never_touches_the_source(paths):
    before = paths["src"].read_bytes()
    out = record(paths["corr"], paths["bak"], VID, "text", "բարև", "բարև ձեզ")
    assert out["status"] == "created"
    assert paths["src"].read_bytes() == before      # the whole point of the overlay
    df = load(paths["corr"])
    assert len(df) == 1
    assert df.iloc[0]["old_value"] == "բարև"
    assert df.iloc[0]["new_value"] == "բարև ձեզ"


def test_re_editing_keeps_the_ORIGINAL_old_value(paths):
    record(paths["corr"], paths["bak"], VID, "text", "բարև", "first")
    out = record(paths["corr"], paths["bak"], VID, "text", "բարև", "second")
    assert out["status"] == "updated"
    df = load(paths["corr"])
    assert len(df) == 1                              # upsert, not append
    # old_value must stay the real source value or the staleness guard breaks.
    assert df.iloc[0]["old_value"] == "բարև"
    assert df.iloc[0]["new_value"] == "second"


def test_setting_a_field_back_to_source_removes_the_correction(paths):
    record(paths["corr"], paths["bak"], VID, "text", "բարև", "changed")
    out = record(paths["corr"], paths["bak"], VID, "text", "բարև", "բարև")
    assert out["status"] == "reverted"
    assert len(load(paths["corr"])) == 0             # overlay stays a list of PENDING changes


def test_no_op_on_an_unedited_field_writes_nothing(paths):
    out = record(paths["corr"], paths["bak"], VID, "text", "բարև", "բարև")
    assert out["status"] == "unchanged"
    assert not paths["corr"].exists()


def test_previous_overlay_is_backed_up_before_each_write(paths):
    record(paths["corr"], paths["bak"], VID, "text", "բարև", "one")
    record(paths["corr"], paths["bak"], VID, "text", "բարև", "two")
    record(paths["corr"], paths["bak"], VID, "text", "բարև", "three")
    # First write has nothing to back up; the next two do.
    assert len(list(paths["bak"].glob("corrections_*.csv"))) == 2


def test_edits_to_different_fields_coexist(paths):
    record(paths["corr"], paths["bak"], VID, "text", "բարև", "new text")
    record(paths["corr"], paths["bak"], VID, "location", "Տուն", "Փողոց")
    assert len(load(paths["corr"])) == 2


def test_plan_marks_a_correction_stale_when_the_source_moved(paths):
    record(paths["corr"], paths["bak"], VID, "text", "բարև", "new")
    # Someone rebuilds or hand-edits the CSV underneath.
    df = pd.read_csv(paths["src"], dtype=str, keep_default_na=False)
    df.loc[df.video_id == VID, "text"] = "changed elsewhere"
    df.to_csv(paths["src"], index=False)

    p = plan(paths["src"], paths["corr"])
    assert p["apply"] == []
    assert len(p["stale"]) == 1
    assert p["stale"][0]["current_value"] == "changed elsewhere"


def test_plan_flags_an_unknown_video_id(paths):
    record(paths["corr"], paths["bak"], "zzzzzzzzzzz", "text", "", "orphan")
    p = plan(paths["src"], paths["corr"])
    assert len(p["unknown"]) == 1
    assert p["apply"] == []


def test_plan_lists_applicable_corrections(paths):
    record(paths["corr"], paths["bak"], VID, "text", "բարև", "new")
    record(paths["corr"], paths["bak"], "bbbbbbbbbbb", "location", "", "Տուն")
    p = plan(paths["src"], paths["corr"])
    assert len(p["apply"]) == 2
    assert p["stale"] == [] and p["unknown"] == []


def test_clean_normalises_missing_values():
    assert clean(None) == "" and clean(float("nan")) == "" and clean("nan") == ""
    assert clean("  keep  ") == "  keep  "        # does NOT strip; whitespace may be meaningful
