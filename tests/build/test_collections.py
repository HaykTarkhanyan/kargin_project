import pytest

from scripts.kargin_build.collections import build_collections, parse_slugs


def _def(slug="cards", name="Թուղթ", description="Խաղում են", sort="1", **kw):
    return {"slug": slug, "name_hy": name, "description_hy": description, "sort": sort, **kw}


def _row(video_id="abc", collections="cards", id="001", duplicate_of="", **kw):
    return {"id": id, "video_id": video_id, "collections": collections,
            "duplicate_of": duplicate_of, **kw}


def test_parse_slugs_trims_blanks_and_dedupes():
    assert parse_slugs("cards; tv") == ["cards", "tv"]
    assert parse_slugs(" cards ;; cards ") == ["cards"]
    assert parse_slugs("") == []
    assert parse_slugs(None) == []


def test_builds_in_sort_order_with_members():
    out = build_collections(
        [_row("a", "tv"), _row("b", "cards"), _row("c", "tv")],
        [_def("tv", "Հեռուստացույց", "Դիտում են", "2"), _def("cards", sort="1")],
    )
    assert [c["slug"] for c in out] == ["cards", "tv"]
    assert out[0]["sketchIds"] == ["b"]
    assert out[1]["sketchIds"] == ["a", "c"]
    assert out[1]["name"] == "Հեռուստացույց"
    assert out[1]["description"] == "Դիտում են"


def test_a_sketch_can_be_in_several_collections():
    out = build_collections([_row("a", "cards;doctor")],
                            [_def("cards"), _def("doctor", sort="2")])
    assert out[0]["sketchIds"] == ["a"]
    assert out[1]["sketchIds"] == ["a"]


def test_rows_without_collections_are_ignored():
    out = build_collections([_row("a", "cards"), _row("b", ""), _row("c", "   ")], [_def()])
    assert out[0]["sketchIds"] == ["a"]


def test_undefined_slug_fails_loudly():
    with pytest.raises(ValueError, match="does not define"):
        build_collections([_row("a", "carsd")], [_def("cards")])


def test_collection_without_members_fails_loudly():
    with pytest.raises(ValueError, match="no members"):
        build_collections([_row("a", "cards")], [_def("cards"), _def("tv", sort="2")])


def test_duplicate_slug_in_definitions_fails():
    with pytest.raises(ValueError, match="duplicate slug"):
        build_collections([_row("a", "cards")], [_def("cards"), _def("cards", sort="2")])


@pytest.mark.parametrize("slug", ["Cards", "traffic-police", "թուղթ", ""])
def test_bad_slug_charset_fails(slug):
    with pytest.raises(ValueError, match="bad slug"):
        build_collections([_row("a", "cards")], [_def(slug)])


def test_slug_whitespace_is_trimmed_not_rejected():
    # Hand-edited CSVs collect stray spaces. Both sides trim, so they still meet.
    out = build_collections([_row("a", " cards ")], [_def(" cards ")])
    assert out[0]["slug"] == "cards"
    assert out[0]["sketchIds"] == ["a"]


def test_member_without_video_id_fails():
    with pytest.raises(ValueError, match="no video_id"):
        build_collections([_row("", "cards")], [_def()])


def test_duplicate_sketch_as_member_fails():
    with pytest.raises(ValueError, match="duplicate of"):
        build_collections([_row("a", "cards"), _row("b", "cards", duplicate_of="a")], [_def()])


def test_non_integer_sort_fails():
    with pytest.raises(ValueError, match="non-integer sort"):
        build_collections([_row("a", "cards")], [_def(sort="first")])


@pytest.mark.parametrize("field,value", [("name", ""), ("description", "")])
def test_missing_copy_fails(field, value):
    with pytest.raises(ValueError, match=f"no {'name_hy' if field == 'name' else 'description_hy'}"):
        build_collections([_row("a", "cards")], [_def(**{field: value})])


def test_no_definitions_at_all_fails():
    with pytest.raises(ValueError, match="defines no collections"):
        build_collections([_row("a", "cards")], [])
