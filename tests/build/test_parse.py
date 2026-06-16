from scripts.kargin_build.parse import extract_video_id, parse_seq, split_lines


def test_extract_video_id_watch_url():
    assert extract_video_id("https://www.youtube.com/watch?v=ofvCL_U2Er0&list=x") == "ofvCL_U2Er0"

def test_extract_video_id_short_url():
    assert extract_video_id("https://youtu.be/hp0U2719O0A?t=10") == "hp0U2719O0A"

def test_extract_video_id_none_on_garbage():
    assert extract_video_id("not a url") is None
    assert extract_video_id(None) is None

def test_parse_seq_from_title():
    assert parse_seq("Kargin Haghordum sketch 579 (Hayko Mko)") == 579

def test_parse_seq_missing_returns_none():
    assert parse_seq("Kargin Haghordum - Dombel (Hayko Mko)") is None

def test_split_lines_semicolon_and_armenian_fullstop():
    assert split_lines("բարև; ոնց ես։ լավ") == ["բարև", "ոնց ես", "լավ"]

def test_split_lines_does_not_split_on_hyphen():
    assert split_lines("1-2 հատ") == ["1-2 հատ"]

def test_split_lines_empty():
    assert split_lines("") == []
    assert split_lines(None) == []
