import json

import pytest

from kargin_build.visual import load_visual

FULL = {
    "video_id": "abc123def45",
    "indoor_outdoor": "outdoor",
    "day_night": "day",
    "people_count": "2",
    "has_crowd_or_extras": False,
    "animals": ["donkey"],
    "vehicles": [],
    "location_fine": "village pasture",
    "character_types": ["villager"],
    "drag": False,
    "key_props": ["boombox"],
    "physicality": "physical",
    "scene_structure": {"settings": 2, "repeating_gag": False},
    "visual_synopsis": "A man leads a donkey across farmland.",
    "best_frame_ts": "01:10",
    "confidence": "medium",
    "needs_audio": True,
}


def _write(dir_path, name, **overrides):
    d = {**FULL, **overrides}
    (dir_path / name).write_text(json.dumps(d), encoding="utf-8")
    return d


def test_missing_dir_returns_empty(tmp_path):
    assert load_visual(tmp_path / "nope") == {}


def test_ships_site_fields_and_omits_empty(tmp_path):
    _write(tmp_path, "051_abc123def45.json")
    v = load_visual(tmp_path)["abc123def45"]
    assert v["locationFine"] == "village pasture"
    assert v["synopsis"].startswith("A man leads")
    assert v["animals"] == ["donkey"]
    assert v["keyProps"] == ["boombox"]
    # Empty vehicles and false drag are omitted, not shipped as []/false.
    assert "vehicles" not in v and "drag" not in v
    # Repo-only bookkeeping never reaches the payload.
    assert "needs_audio" not in v and "people_count" not in v


def test_drag_true_ships(tmp_path):
    _write(tmp_path, "051_abc123def45.json", drag=True)
    assert load_visual(tmp_path)["abc123def45"]["drag"] is True


def test_duplicate_video_id_fails_loudly(tmp_path):
    _write(tmp_path, "001_abc123def45.json")
    _write(tmp_path, "002_abc123def45.json")
    with pytest.raises(ValueError, match="duplicate"):
        load_visual(tmp_path)
