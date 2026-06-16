"""Pure parsing helpers for the site-data build. No I/O."""
import re

_VIDEO_ID = re.compile(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})")
_SEQ = re.compile(r"(?:sketch|սքեթչ)\s+(\d+)", re.IGNORECASE)
# Real separators in the curated `text`: ';' (~60%) and '։' (Armenian full stop, ~30%).
# Deliberately NOT bare '-' (would mangle "1-2").
_LINE_SPLIT = re.compile(r"[;։]")


def extract_video_id(url):
    if not isinstance(url, str):
        return None
    m = _VIDEO_ID.search(url)
    return m.group(1) if m else None


def parse_seq(title):
    if not isinstance(title, str):
        return None
    m = _SEQ.search(title)
    return int(m.group(1)) if m else None


def split_lines(text):
    if not isinstance(text, str):
        return []
    return [seg.strip() for seg in _LINE_SPLIT.split(text) if seg.strip()]
