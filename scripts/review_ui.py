"""Local curation UI: review each video and correct its curated fields.

Reads kargin_eng.csv. NEVER writes it. Edits go to data/corrections.csv as an
overlay (see kargin_review/store.py); merging them into the source is a separate
deliberate step via scripts/apply_corrections.py.

Binds to 127.0.0.1 only — this exposes your source data and has no auth, so it
must not be reachable from the network.

Usage:
    uv run --group review python scripts/review_ui.py
    uv run --group review python scripts/review_ui.py --port 5055
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, render_template, request

from kargin_review.store import (
    EDITABLE_FIELDS, FIELD_KIND, STATUS_FALSE, STATUS_FIELD,
    as_map, clean, load, record_many,
)

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "review_ui.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

app = Flask(__name__, template_folder=str(Path(__file__).parent / "review_templates"))
CFG: dict = {}


def rows() -> list[dict]:
    """kargin_eng.csv as plain string dicts, re-read per request.

    Deliberately not cached: the file may be rebuilt or edited underneath, and
    serving a stale copy would let the UI record corrections against values that
    are no longer there.
    """
    df = pd.read_csv(CFG["source"], dtype=str, keep_default_na=False)
    return df.to_dict("records")


def field_options(all_rows: list[dict]) -> dict[str, list[str]]:
    """Distinct non-empty values per select/datalist field, most common first.

    Derived from the CSV rather than hardcoded so the choices track the data:
    a value added today shows up in the dropdown without a code change.
    """
    out: dict[str, list[str]] = {}
    for field, kind in FIELD_KIND.items():
        if kind not in ("select", "combo"):
            continue
        counts: dict[str, int] = {}
        for r in all_rows:
            v = clean(r.get(field))
            if v:
                counts[v] = counts.get(v, 0) + 1
        out[field] = sorted(counts, key=lambda v: (-counts[v], v))
    return out


@app.get("/")
def index():
    return render_template(
        "review.html",
        fields=list(EDITABLE_FIELDS),
        kinds=FIELD_KIND,
        options=field_options(rows()),
    )


def word_count(text: str) -> int:
    return len(clean(text).split())


@app.get("/api/videos")
def api_videos():
    """Sidebar index plus the status distribution.

    `status` reflects any pending correction, not just the CSV — otherwise a row
    you just marked reviewed would still show as unreviewed until you applied.
    """
    corr = as_map(load(CFG["corrections"]))
    edited = {k[0] for k in corr}

    items = []
    for r in rows():
        vid = r["video_id"]
        pending = corr.get((vid, STATUS_FIELD))
        status = clean(pending["new_value"]) if pending else clean(r.get(STATUS_FIELD))
        items.append({
            "video_id": vid,
            "id": r.get("id", ""),
            "title": r.get("titles", ""),
            "words": word_count(r.get("text")),
            "status": status or STATUS_FALSE,
            "edited": vid in edited,
            # From the audio-fingerprint pass: this sketch is the same recording
            # as another upload, so its curation may already exist elsewhere.
            "duplicate": bool(clean(r.get("duplicate_of"))),
        })

    # Shortest first: the sketches with least dialogue are the ones most likely
    # to be missing curation, so they are where review time pays off.
    items.sort(key=lambda it: (it["words"], it["id"]))

    dist: dict[str, int] = {}
    for it in items:
        dist[it["status"]] = dist.get(it["status"], 0) + 1
    return jsonify({
        "items": items,
        "distribution": dist,
        "edited": len(edited),
        "duplicates": sum(1 for it in items if it["duplicate"]),
    })


@app.get("/api/video/<video_id>")
def api_video(video_id: str):
    row = next((r for r in rows() if r["video_id"] == video_id), None)
    if row is None:
        return jsonify({"error": "unknown video_id"}), 404
    corr = as_map(load(CFG["corrections"]))
    fields = {}
    for f in EDITABLE_FIELDS:
        source = clean(row.get(f))
        c = corr.get((video_id, f))
        fields[f] = {
            "source": source,
            "value": c["new_value"] if c else source,
            "edited": bool(c),
        }
    return jsonify({
        "video_id": video_id,
        "id": row.get("id", ""),
        # Read-only: shown as the heading so you know what you are reviewing,
        # but not editable — it is YouTube's title, not curation output.
        "title": clean(row.get("titles")),
        "link": row.get("links", ""),
        "duplicate_of": clean(row.get("duplicate_of")),
        "fields": fields,
    })


@app.post("/api/video/<video_id>")
def api_save(video_id: str):
    """Record edits for one video. Writes only data/corrections.csv."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("fields"), dict):
        return jsonify({"error": "expected {\"fields\": {name: value}}"}), 400

    row = next((r for r in rows() if r["video_id"] == video_id), None)
    if row is None:
        return jsonify({"error": "unknown video_id"}), 404

    bad = [f for f in payload["fields"] if f not in EDITABLE_FIELDS]
    if bad:
        # Reject the whole request rather than silently saving the valid subset.
        return jsonify({"error": f"not editable: {bad}"}), 400

    for field, value in payload["fields"].items():
        if not isinstance(value, str):
            return jsonify({"error": f"{field}: expected a string"}), 400

    # One batched write: a five-field save should not produce five rewrites and
    # five backup files, and the whole save should land or not at all.
    results = record_many(
        CFG["corrections"], CFG["backups"], video_id,
        {f: (clean(row.get(f)), v) for f, v in payload["fields"].items()},
    )

    changed = {f: s for f, s in results.items() if s != "unchanged"}
    if changed:
        logging.info(f"saved {video_id}: {changed}")
    return jsonify({"saved": results})


@app.get("/api/corrections")
def api_corrections():
    df = load(CFG["corrections"])
    return jsonify({"count": len(df), "rows": df.to_dict("records")})


def main(source: Path, corrections: Path, backups: Path, port: int) -> int:
    if not source.exists():
        logging.error(f"source not found: {source}")
        return 2
    CFG.update(source=source, corrections=corrections, backups=backups)
    n = len(rows())
    logging.info(f"{n} videos from {source} (read-only)")
    logging.info(f"edits -> {corrections}   backups -> {backups}")
    logging.info(f"kargin_eng.csv is NEVER written here; use scripts/apply_corrections.py")
    logging.info(f"open http://127.0.0.1:{port}/")
    app.run(host="127.0.0.1", port=port, debug=False)
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", default=Path("kargin_eng.csv"), type=Path)
    p.add_argument("--corrections", default=Path("data/corrections.csv"), type=Path)
    p.add_argument("--backups", default=Path("data/backups"), type=Path)
    p.add_argument("--port", type=int, default=5050)
    a = p.parse_args()
    sys.exit(main(a.source, a.corrections, a.backups, a.port))
