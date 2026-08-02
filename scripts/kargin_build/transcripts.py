"""Fold data/transcripts/*.hy.json into the site payload.

Only Armenian (`hy`) transcripts are used. The archive also holds 230 caption
files in other languages, but those are YouTube's language detection failing on
Armenian speech -- they contain `[Muzik]` markers or phonetic hallucination, not
dialogue, and shipping them would put nonsense on the page.

Transcripts are kept SEPARATE from the curated `text` field rather than merged
into it. They are different kinds of evidence: `text` is hand-written by a human
who watched the sketch, a transcript is machine output with known errors. A
reader deserves to know which they are looking at, and a future correction pass
must not have to guess which words a person actually chose.

Measured for context: where a video has both, curation is about as complete as
ASR (median length ratio 0.95) and independently worded (median Jaccard 0.47 --
similar speech, different spelling). So a transcript mostly matters where
curation is thin or absent.
"""
import json
import re

# Armenian block. Used to judge whether a transcript carries real dialogue
# rather than stray Latin/Cyrillic fragments from a music-only sketch.
ARMENIAN = re.compile(r"[԰-֏]")

# Below this a transcript is noise, not dialogue: the worst of the batch came
# back with a single Armenian character across three minutes of audio.
MIN_ARMENIAN_CHARS = 100


def load_transcripts(dir_path):
    """{video_id: {text, source, events, armenianChars}}.

    Returns {} when the directory is absent -- transcripts are an optional,
    partially-complete pass and the site builds fine without them.
    """
    if not dir_path.exists():
        return {}

    out = {}
    for p in sorted(dir_path.glob("*.hy.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        vid, text = d.get("video_id"), (d.get("full_text") or "").strip()
        if not vid or not text:
            continue
        arm = len(ARMENIAN.findall(text))
        if arm < MIN_ARMENIAN_CHARS:
            continue
        # Prefer the richer transcript if a video somehow has two.
        prev = out.get(vid)
        if prev and prev["armenianChars"] >= arm:
            continue
        out[vid] = {
            "text": text,
            # "batch_reupload" (we uploaded the audio and set the language) vs
            # "youtube_fetch" (the sketch's own page already had hy captions).
            "source": d.get("source", "youtube_fetch"),
            "events": d.get("n_events", 0),
            "armenianChars": arm,
        }
    return out
