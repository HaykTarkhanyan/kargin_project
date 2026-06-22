import pandas as pd
from scripts.kargin_build.assemble import row_to_sketch, ACTOR_ALLOWLIST, ACTOR_TYPOS


def _row(**kw):
    base = dict(titles="Kargin Haghordum sketch 663 (Hayko Mko)",
                links="https://youtu.be/ofvCL_U2Er0", text="բարև; ոնց ես",
                text_common="արա էսի ուզբեկ ա", main_actors="Հայկո, Մկո",
                roles_names="", location="Տուն", lighting="", languages="հայերեն",
                duration_sec=242, view_count=1358199, upload_date="20130410.0")
    base.update(kw)
    return pd.Series(base)


def test_row_to_sketch_core_fields():
    s = row_to_sketch(_row(), ACTOR_ALLOWLIST, ACTOR_TYPOS)
    assert s["id"] == "ofvCL_U2Er0"
    assert s["videoId"] == "ofvCL_U2Er0"
    assert s["title"] == "Kargin Haghordum sketch 663 (Hayko Mko)"   # REAL title, not fabricated
    assert s["seq"] == 663
    assert s["actors"] == ["Հայկո", "Մկո"]
    assert s["location"] == "Տուն"
    assert s["durationSec"] == 242
    assert s["viewCount"] == 1358199
    assert s["uploadDate"] == "2013-04-10"
    assert s["thumbnail"].endswith("/ofvCL_U2Er0/mqdefault.jpg")
    assert "lines" not in s and "segments" not in s   # derived/empty fields dropped from the payload

def test_row_to_sketch_empty_text():
    s = row_to_sketch(_row(text=""), ACTOR_ALLOWLIST, ACTOR_TYPOS)
    assert s["text"] == ""

def test_build_all_rejects_duplicate_video_ids(tmp_path):
    import pytest
    from scripts.kargin_build.assemble import build_all
    k, m = tmp_path / "k.csv", tmp_path / "m.csv"
    pd.DataFrame({"links": ["https://youtu.be/aaaaaaaaaaa"], "titles": ["t"], "text": [""],
                  "text_common": [""], "main_actors": [""], "roles_names": [""],
                  "location": [""], "lighting": [""], "languages": [""]}).to_csv(k, index=False)
    pd.DataFrame({"video_id": ["aaaaaaaaaaa", "aaaaaaaaaaa"], "duration_sec": [10, 10],
                  "view_count": [1, 1], "upload_date": ["20200101.0", "20200101.0"]}).to_csv(m, index=False)
    with pytest.raises(ValueError, match="duplicate"):
        build_all(k, m)
