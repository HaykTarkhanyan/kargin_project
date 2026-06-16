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
    assert s["lines"] == ["բարև", "ոնց ես"]
    assert s["actors"] == ["Հայկո", "Մկո"]
    assert s["location"] == "Տուն"
    assert s["durationSec"] == 242
    assert s["viewCount"] == 1358199
    assert s["uploadDate"] == "2013-04-10"
    assert s["thumbnail"].endswith("/ofvCL_U2Er0/mqdefault.jpg")
    assert s["segments"] == []

def test_row_to_sketch_empty_text_yields_no_lines():
    s = row_to_sketch(_row(text=""), ACTOR_ALLOWLIST, ACTOR_TYPOS)
    assert s["lines"] == [] and s["text"] == ""
