"""Split the batch video's caption track back into per-video transcripts.

Takes the single JSON3 caption file YouTube generates for the uploaded batch
video and the manifest that describes how it was assembled, and writes one
transcript per source video in the same schema as convert_transcripts.py, so
these files are interchangeable with the 315 fetched from original uploads.

Assignment is by TIMESTAMP against the manifest's start_sec/end_sec, not by
reading anything on screen -- captions come from audio, so the on-screen id
never appears in the track. An event is assigned by its MIDPOINT: ASR routinely
emits a caption whose window overlaps a clip boundary by a fraction of a second,
and midpoint puts it with the clip that holds most of it instead of always
spilling forward.

Timestamps are rebased to clip-local time, so a caption 4 minutes into clip 3
comes out at 0:23 like it would have from the original video.

Provenance is recorded in each file: these came from a re-upload, not from the
sketch's own YouTube page, and a later reader should not have to guess.

Usage:
    uv run python scripts/split_batch_transcript.py --captions batch.hy-orig.json3
    uv run python scripts/split_batch_transcript.py --captions batch.json3 --dry-run
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
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "split_batch_transcript.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)


def read_json3(path: Path) -> list[dict]:
    """JSON3 events -> [{start, end, text}] in batch-global seconds."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if "events" not in raw:
        raise ValueError(f"{path} has no 'events' key -- is this really a JSON3 caption file?")
    out = []
    for ev in raw["events"]:
        segs = ev.get("segs")
        if not segs:
            continue
        text = "".join(s.get("utf8", "") for s in segs).strip()
        if not text:
            continue
        start = (ev.get("tStartMs") or 0) / 1000.0
        out.append({
            "start": start,
            "end": start + (ev.get("dDurationMs") or 0) / 1000.0,
            "text": text,
        })
    return out


def assign(events: list[dict], rows: list[dict]) -> tuple[dict[int, list], list[dict]]:
    """Bucket events by manifest seq. Returns (by_seq, unassigned).

    Unassigned events are a real signal, not noise to swallow: more than a
    handful means the rendered audio drifted from the manifest and every offset
    after the drift is suspect.
    """
    by_seq: dict[int, list] = {r["seq"]: [] for r in rows}
    unassigned = []
    for e in events:
        mid = (e["start"] + e["end"]) / 2 if e["end"] > e["start"] else e["start"]
        hit = next((r for r in rows if r["start_sec"] <= mid < r["end_sec"]), None)
        if hit is None:
            unassigned.append(e)
            continue
        by_seq[hit["seq"]].append(e)
    return by_seq, unassigned


def build(row: dict, events: list[dict], lang: str, batch_name: str) -> dict:
    """One per-video transcript, timestamps rebased to clip-local seconds."""
    dur = row["duration_sec"]
    local = []
    for e in events:
        start = max(0.0, e["start"] - row["start_sec"])
        end = min(dur, e["end"] - row["start_sec"])
        local.append({"start": round(start, 3), "end": round(end, 3), "text": e["text"]})
    return {
        "video_id": row["video_id"],
        "seq": int(row["seq"]),
        "title": row["title"],
        "source_lang": lang,
        "n_events": len(local),
        "duration_sec": round(dur, 3),
        "full_text": "\n".join(e["text"] for e in local),
        "events": local,
        # Provenance: not fetched from this sketch's own YouTube page.
        "source": "batch_reupload",
        "batch_file": batch_name,
        "batch_start_sec": row["start_sec"],
    }


def main(captions: Path, manifest_path: Path, out_dir: Path, lang: str, dry_run: bool) -> int:
    if not captions.exists():
        logging.error(f"caption file not found: {captions}")
        return 2
    if not manifest_path.exists():
        logging.error(f"manifest not found: {manifest_path}")
        return 2

    rows = pd.read_csv(manifest_path).to_dict("records")
    events = read_json3(captions)
    logging.info(f"{len(events)} caption events over {len(rows)} clips")

    by_seq, unassigned = assign(events, rows)
    if unassigned:
        logging.warning(f"{len(unassigned)} events fell outside every clip window "
                        f"(first at {unassigned[0]['start']:.1f}s) -- "
                        "expected only past the final clip's end")

    empty = [r["seq"] for r in rows if not by_seq[r["seq"]]]
    if empty:
        logging.warning(f"{len(empty)} clips got NO captions: seq {empty}. "
                        "Silence, music-only, or ASR gave up on that stretch.")

    out_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for r in rows:
        entry = build(r, by_seq[r["seq"]], lang, captions.name)
        # Reuse the original audio filename stem so these sit alongside the
        # existing transcripts under the same naming convention.
        stem = Path(r["audio_path"]).stem
        dest = out_dir / f"{stem}.{lang}.json"
        chars = len(entry["full_text"])
        logging.info(f"  seq {r['seq']:02d}  {r['video_id']}  "
                     f"{entry['n_events']:4d} events  {chars:6d} chars")
        if not dry_run:
            dest.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
            written += 1

    total_chars = sum(len(build(r, by_seq[r["seq"]], lang, captions.name)["full_text"]) for r in rows)
    logging.info(f"{'would write' if dry_run else 'wrote'} {len(rows) if dry_run else written} "
                 f"transcripts to {out_dir}, {total_chars:,} chars total")
    if dry_run:
        logging.info("dry run -- nothing written. Re-run without --dry-run to save.")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--captions", required=True, type=Path,
                   help="JSON3 caption file downloaded from the uploaded batch video")
    p.add_argument("--manifest", default=Path("data/transcription_batch/manifest.csv"), type=Path)
    p.add_argument("--out", default=Path("data/transcripts"), type=Path)
    p.add_argument("--lang", default="hy")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    sys.exit(main(a.captions, a.manifest, a.out, a.lang, a.dry_run))
