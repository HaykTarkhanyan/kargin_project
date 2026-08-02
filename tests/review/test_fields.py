"""Field kinds and the options the UI derives from the data."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from kargin_review.store import EDITABLE_FIELDS, FIELD_KIND     # noqa: E402
import review_ui                                                # noqa: E402


def test_titles_is_not_editable():
    assert "titles" not in EDITABLE_FIELDS and "titles" not in FIELD_KIND


def test_every_editable_field_declares_a_known_kind():
    assert set(EDITABLE_FIELDS) == set(FIELD_KIND)
    assert set(FIELD_KIND.values()) <= {"textarea", "text", "select", "combo"}


@pytest.mark.parametrize("field,kind", [
    ("lighting", "select"), ("languages", "select"), ("done", "select"),
    # combo, not datalist: a bare <datalist> has no visible affordance and reads
    # as a dead text field.
    ("location", "combo"), ("main_actors_count", "combo"),
    ("text", "textarea"), ("text_common", "textarea"),
])
def test_field_kinds(field, kind):
    assert FIELD_KIND[field] == kind


def test_options_come_from_the_data_most_common_first():
    rows = [
        {"lighting": "մութ", "location": "Տուն", "done": "1.0"},
        {"lighting": "լուսավոր", "location": "Տուն", "done": "1.0"},
        {"lighting": "լուսավոր", "location": "Դուրս", "done": "0.0"},
        {"lighting": "լուսավոր", "location": "", "done": ""},
    ]
    opts = review_ui.field_options(rows)
    assert opts["lighting"] == ["լուսավոր", "մութ"]      # 3 before 1
    assert opts["location"] == ["Տուն", "Դուրս"]         # empties excluded
    assert opts["done"] == ["1.0", "0.0"]


def test_options_only_cover_choosable_fields():
    opts = review_ui.field_options([{f: "x" for f in EDITABLE_FIELDS}])
    assert set(opts) == {f for f, k in FIELD_KIND.items() if k in ("select", "combo")}
    assert "text" not in opts


def test_status_final_is_an_editable_select():
    assert FIELD_KIND["status_final"] == "select"


@pytest.mark.parametrize("text,expected", [
    ("", 0), ("   ", 0), ("բարև", 1), ("բարև ձեզ", 2),
    ("բարև; ոնց ես", 3),                    # the ';' rides along with a word
    ("a  b\n c", 3),                         # collapses any whitespace run
])
def test_word_count(text, expected):
    assert review_ui.word_count(text) == expected


def test_word_count_handles_missing_values():
    assert review_ui.word_count(None) == 0
    assert review_ui.word_count(float("nan")) == 0


def test_real_csv_yields_sane_option_sets():
    src = Path(__file__).resolve().parents[2] / "kargin_eng.csv"
    rows = pd.read_csv(src, dtype=str, keep_default_na=False).to_dict("records")
    opts = review_ui.field_options(rows)
    # `done` really is binary in the curated data.
    assert set(opts["done"]) == {"1.0", "0.0"}
    assert opts["lighting"][0] == "լուսավոր"
    assert "" not in opts["location"]
