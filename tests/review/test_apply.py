"""apply_corrections is the only writer of kargin_eng.csv, so prove it is surgical."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from apply_corrections import main as apply_main            # noqa: E402
from kargin_review.store import record, record_many         # noqa: E402

VID = "aaaaaaaaaaa"


@pytest.fixture
def env(tmp_path):
    src = tmp_path / "kargin_eng.csv"
    pd.DataFrame([
        {"id": f"{i:03d}", "video_id": f"vid{i:08d}", "titles": f"sketch {i}",
         "text": f"text {i}", "text_common": "", "main_actors": "Հայկո",
         "location": "Տուն", "lighting": "", "languages": "հայերեն",
         "main_actors_count": "1", "roles_names": "", "done": "1.0",
         "links": f"https://youtu.be/vid{i:08d}", "duplicate_of": ""}
        for i in range(5)
    ]).to_csv(src, index=False, lineterminator="\r\n")
    return {"src": src, "corr": tmp_path / "corrections.csv",
            "bak": tmp_path / "backups"}


def rows(p):
    return pd.read_csv(p, dtype=str, keep_default_na=False).to_dict("records")


def test_dry_run_writes_nothing(env):
    record(env["corr"], env["bak"], "vid00000002", "text", "text 2", "CHANGED")
    before = env["src"].read_bytes()
    assert apply_main(env["src"], env["corr"], env["bak"], write=False, clear=False) == 0
    assert env["src"].read_bytes() == before


def test_write_changes_only_the_targeted_cell(env):
    before = rows(env["src"])
    record(env["corr"], env["bak"], "vid00000002", "text", "text 2", "CHANGED")
    assert apply_main(env["src"], env["corr"], env["bak"], write=True, clear=False) == 0

    after = rows(env["src"])
    assert len(after) == len(before)
    for i, (b, a) in enumerate(zip(before, after)):
        for col in b:
            if i == 2 and col == "text":
                assert a[col] == "CHANGED"
            else:
                assert a[col] == b[col], f"row {i} column {col} changed unexpectedly"


def test_write_backs_up_the_source_first(env):
    original = env["src"].read_bytes()
    record(env["corr"], env["bak"], "vid00000001", "location", "Տուն", "Փողոց")
    apply_main(env["src"], env["corr"], env["bak"], write=True, clear=False)
    backups = list(env["bak"].glob("kargin_eng_*.csv"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == original          # exact pre-write state


def test_stale_correction_is_refused_and_source_untouched(env):
    record(env["corr"], env["bak"], "vid00000003", "text", "text 3", "MINE")
    # Something else edits the source in between.
    df = pd.read_csv(env["src"], dtype=str, keep_default_na=False)
    df.loc[df.video_id == "vid00000003", "text"] = "THEIRS"
    df.to_csv(env["src"], index=False, lineterminator="\r\n")
    before = env["src"].read_bytes()

    rc = apply_main(env["src"], env["corr"], env["bak"], write=True, clear=False)
    assert rc == 1                                       # non-zero: something needs attention
    assert env["src"].read_bytes() == before             # THEIRS survives, MINE is not applied


def test_clear_drops_only_applied_rows(env):
    record(env["corr"], env["bak"], "vid00000000", "text", "text 0", "A")
    record(env["corr"], env["bak"], "zzzzzzzzzzz", "text", "", "orphan")   # unknown video
    apply_main(env["src"], env["corr"], env["bak"], write=True, clear=True)
    left = pd.read_csv(env["corr"], dtype=str, keep_default_na=False)
    assert list(left["video_id"]) == ["zzzzzzzzzzz"]      # unapplied row is kept


def test_multi_field_save_is_one_backup_and_one_write(env):
    status = record_many(env["corr"], env["bak"], "vid00000004", {
        "text": ("text 4", "new text"),
        "location": ("Տուն", "Փողոց"),
        "lighting": ("", "Ցերեկ"),
    })
    assert status == {"text": "created", "location": "created", "lighting": "created"}
    assert len(pd.read_csv(env["corr"])) == 3
    # First write has nothing to back up, so a single batched save leaves none.
    assert list(env["bak"].glob("corrections_*.csv")) == []


def test_a_correction_naming_a_missing_column_is_not_applied(env):
    # main_actors_count exists here; simulate a source that lacks the column.
    record(env["corr"], env["bak"], "vid00000000", "text_common", "", "x")
    df = pd.read_csv(env["src"], dtype=str, keep_default_na=False).drop(columns=["text_common"])
    df.to_csv(env["src"], index=False, lineterminator="\r\n")
    before = env["src"].read_bytes()

    rc = apply_main(env["src"], env["corr"], env["bak"], write=True, clear=False)
    assert rc == 1
    assert env["src"].read_bytes() == before             # no column silently created
