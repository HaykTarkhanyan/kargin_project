"""Folding machine transcripts into the site payload."""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from kargin_build.assemble import build_all, MIN_TRANSCRIPT_NOVELTY   # noqa: E402
from kargin_build.transcripts import (                                # noqa: E402
    load_transcripts, novelty, MIN_ARMENIAN_CHARS,
)

ARM = "բարև ձեզ սիրելի հանդիսատես ինչպես եք "

# Distinct sentences, so novelty is meaningful. Repeating one line would make
# every transcript 0% new no matter how long it is.
LINES_A = ("բարև ձեզ սիրելի հանդիսատես\nինչպես եք այսօր բոլորդ\n"
           "շատ ուրախ եմ տեսնել\nեկեք սկսենք մեր հաղորդումը\n"
           "այսօր ունենք հետաքրքիր հյուր\nխնդրում եմ ծափահարեք\n")
LINES_B = ("երեկ գնացի խանութ գնումներ անելու\nվաճառողը ասաց որ չկա\n"
           "տուն վերադարձա դատարկ ձեռքով\nկինս շատ բարկացավ ինձ վրա\n"
           "ասաց նորից պիտի գնաս վաղը\nչեմ ուզում կրկին վիճել\n")


def write(d: Path, name: str, video_id: str, text: str, source="youtube_fetch", events=3):
    (d / name).write_text(json.dumps({
        "video_id": video_id, "seq": 1, "title": "t", "source_lang": "hy",
        "n_events": events, "duration_sec": 100.0, "full_text": text,
        "events": [], "source": source,
    }, ensure_ascii=False), encoding="utf-8")


def test_missing_directory_is_not_fatal(tmp_path):
    # Transcripts are an optional pass; the site must still build without them.
    assert load_transcripts(tmp_path / "nope") == {}


def test_loads_and_reports_source(tmp_path):
    write(tmp_path, "a.hy.json", "vid1", ARM * 5, source="batch_reupload")
    got = load_transcripts(tmp_path)
    assert got["vid1"]["source"] == "batch_reupload"
    assert got["vid1"]["armenianChars"] > MIN_ARMENIAN_CHARS


def test_drops_transcripts_with_almost_no_armenian(tmp_path):
    # The real failure mode: a music-only sketch came back as "Ah. ե เฮ".
    write(tmp_path, "junk.hy.json", "vid2", "Ah. ե Здравствуйте hello there")
    assert load_transcripts(tmp_path) == {}


def test_ignores_non_armenian_caption_files(tmp_path):
    # 230 such files exist and hold [Muzik] markers, not dialogue.
    write(tmp_path, "b.tr.json", "vid3", ARM * 5)
    assert load_transcripts(tmp_path) == {}


def test_keeps_the_richer_of_two_transcripts(tmp_path):
    write(tmp_path, "a.hy.json", "dup", ARM * 3)
    write(tmp_path, "z.hy.json", "dup", ARM * 9)
    assert load_transcripts(tmp_path)["dup"]["armenianChars"] > len(ARM) * 6


def _payload(tmp_path, curated_text, transcript_text):
    k = tmp_path / "k.csv"
    pd.DataFrame([{
        "titles": "sketch 1", "links": "https://youtu.be/aaaaaaaaaaa",
        "text": curated_text, "text_common": "", "main_actors": "", "roles_names": "",
        "location": "", "lighting": "", "languages": "",
    }]).to_csv(k, index=False)
    m = tmp_path / "m.csv"
    pd.DataFrame([{"video_id": "aaaaaaaaaaa", "duration_sec": 100,
                   "view_count": 1, "upload_date": "20130410"}]).to_csv(m, index=False)
    td = tmp_path / "tr"
    td.mkdir()
    write(td, "a.hy.json", "aaaaaaaaaaa", transcript_text)
    return build_all(k, m, transcripts_dir=td)[0]


def test_transcript_attached_when_there_is_no_curated_dialogue(tmp_path):
    s = _payload(tmp_path, "", LINES_A)
    assert s["transcript"]["text"]
    assert s["transcript"]["novelty"] == 1.0


def test_transcript_omitted_when_curation_already_says_the_same_thing(tmp_path):
    s = _payload(tmp_path, LINES_A, LINES_A)
    assert "transcript" not in s


def test_transcript_attached_when_it_says_something_new(tmp_path):
    # The case the old length rule got wrong: same length, different content.
    s = _payload(tmp_path, LINES_A, LINES_B)
    assert "transcript" in s


def test_same_length_does_not_imply_same_content(tmp_path):
    # Both texts are the same size, so a length-ratio test would call these
    # equivalent and drop the transcript. 26 of 31 pilot videos were lost this way.
    a, b = LINES_A, LINES_B
    assert abs(len(a) - len(b)) < 0.4 * len(a)
    assert novelty(a, b) > MIN_TRANSCRIPT_NOVELTY


def test_novelty_bounds():
    assert novelty("", LINES_A) == 1.0          # nothing curated: all new
    assert novelty(LINES_A, "") == 0.0          # nothing to add
    assert novelty(LINES_A, LINES_A) == 0.0     # identical
    assert 0 < MIN_TRANSCRIPT_NOVELTY < 1


def test_novelty_tolerates_respelling(tmp_path):
    # ASR spells the same speech differently; a sentence sharing half its words
    # with a curated line must still count as already-known.
    respelled = "բարև ձեզ սիրելի հանդիսատեսներ\nինչպես եք այսօր բոլորդ\n"
    assert novelty(LINES_A, respelled) < MIN_TRANSCRIPT_NOVELTY


def test_real_payload_rescues_sketches_that_had_no_dialogue():
    root = Path(__file__).resolve().parents[2]
    data = json.loads((root / "web/public/data/sketches.json").read_text(encoding="utf-8"))
    rescued = [s for s in data if s.get("transcript") and not s["text"].strip()]
    assert len(rescued) > 50, "the batch re-upload should have rescued ~95 sketches"
    # Every rescued sketch must now carry searchable words.
    assert all(len(s["transcript"]["text"]) > 100 for s in rescued)
