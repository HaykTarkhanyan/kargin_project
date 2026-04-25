"""Convert raw YouTube JSON3 caption files into a flat per-video JSON format.

Reads `data/transcripts_raw/*.json3` (yt-dlp output, nested events/segs schema
with style/positioning we don't need) and writes simplified files to
`data/transcripts/`:

    {
      "video_id": "abc",
      "seq": 1,
      "title": "Kargin Haghordum sketch 326 (Hayko Mko)",
      "source_lang": "hy",
      "n_events": 95,
      "duration_sec": 148.0,
      "full_text": "...",          # concatenated event text, easy to search
      "events": [
        {"start": 0.0, "end": 3.5, "text": "..."},
        ...
      ]
    }

Skips `.no_captions` sentinel files — only videos that have actual captions
get a converted file.

Usage:
    uv run python scripts/convert_transcripts.py
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import pandas as pd


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "convert_transcripts.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)


def parse_filename(name: str) -> tuple[str, str, str] | None:
    """`019_Title_videoid.hy-orig.json3` -> (stem='019_Title_videoid', lang='hy', orig_ext='json3').

    Returns None if the file doesn't match the expected pattern.
    """
    parts = name.rsplit(".", 2)
    if len(parts) != 3:
        return None
    stem, lang_with_orig, ext = parts
    if ext != "json3":
        return None
    # Strip "-orig" suffix; that's how we identified source-lang tracks.
    lang = lang_with_orig.removesuffix("-orig")
    return stem, lang, ext


def extract_seq_and_id(stem: str) -> tuple[int | None, str | None]:
    """`019_Title_videoid` -> (19, 'videoid'). Returns (None, None) on no match."""
    head, _, _ = stem.partition("_")
    try:
        seq = int(head)
    except ValueError:
        return None, None
    # Last 11-char alphanumeric chunk is the video_id.
    tail = stem.rsplit("_", 1)[-1]
    if len(tail) == 11 and all(c.isalnum() or c in "_-" for c in tail):
        return seq, tail
    return seq, None


def convert_one(json3_path: Path, title_lookup: dict[str, str]) -> dict:
    """Parse one JSON3 file into the simplified schema."""
    parsed = parse_filename(json3_path.name)
    if parsed is None:
        raise ValueError(f"unexpected filename pattern: {json3_path.name}")
    stem, lang, _ = parsed
    seq, vid = extract_seq_and_id(stem)

    raw = json.loads(json3_path.read_text(encoding="utf-8"))
    out_events: list[dict] = []
    for ev in raw.get("events", []):
        segs = ev.get("segs")
        if not segs:
            continue
        text = "".join(s.get("utf8", "") for s in segs).strip()
        if not text:
            continue
        start = (ev.get("tStartMs") or 0) / 1000.0
        end = start + (ev.get("dDurationMs") or 0) / 1000.0
        out_events.append({"start": round(start, 3), "end": round(end, 3), "text": text})

    full_text = "\n".join(e["text"] for e in out_events)
    duration = out_events[-1]["end"] if out_events else 0.0

    return {
        "video_id": vid,
        "seq": seq,
        "title": title_lookup.get(vid or "", ""),
        "source_lang": lang,
        "n_events": len(out_events),
        "duration_sec": round(duration, 3),
        "full_text": full_text,
        "events": out_events,
    }


def main(input_dir: Path, output_dir: Path, metadata_csv: Path) -> int:
    if not input_dir.exists():
        logging.error(f"input dir not found: {input_dir}")
        return 2

    title_lookup: dict[str, str] = {}
    if metadata_csv.exists():
        df = pd.read_csv(metadata_csv)
        title_lookup = dict(
            zip(df["video_id"].astype(str), df["title"].fillna("").astype(str))
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    json3_files = sorted(p for p in input_dir.iterdir() if p.suffix == ".json3")
    logging.info(f"found {len(json3_files)} json3 files in {input_dir}")

    ok = 0
    fail = 0
    lang_counts: dict[str, int] = {}
    total_events = 0
    total_chars = 0

    for p in json3_files:
        try:
            entry = convert_one(p, title_lookup)
        except Exception as e:
            fail += 1
            logging.error(f"  fail: {p.name}: {e}")
            continue

        # Output filename mirrors input but drops `-orig` and uses `.json` ext.
        out_name = (
            f"{entry['seq']:03d}_"
            + p.name.split("_", 1)[1].rsplit(".", 2)[0]
            + f".{entry['source_lang']}.json"
        )
        out_path = output_dir / out_name
        out_path.write_text(
            json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        ok += 1
        lang_counts[entry["source_lang"]] = lang_counts.get(entry["source_lang"], 0) + 1
        total_events += entry["n_events"]
        total_chars += len(entry["full_text"])

    logging.info(f"done. converted {ok}, failed {fail}")
    if lang_counts:
        logging.info("source-lang distribution:")
        for l, c in sorted(lang_counts.items(), key=lambda x: -x[1]):
            logging.info(f"  {l:6}  {c}")
    logging.info(f"total events: {total_events}, total chars: {total_chars:,}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", default=Path("data/transcripts_raw"), type=Path)
    p.add_argument("--output", default=Path("data/transcripts"), type=Path)
    p.add_argument("--metadata", default=Path("data/youtube_metadata.csv"), type=Path)
    args = p.parse_args()
    sys.exit(main(args.input, args.output, args.metadata))
