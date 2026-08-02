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

from kargin_review.store import EDITABLE_FIELDS, as_map, clean, load, record

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


@app.get("/")
def index():
    return render_template("review.html", fields=list(EDITABLE_FIELDS))


@app.get("/api/videos")
def api_videos():
    """Index for the sidebar: id, title, and whether it has pending edits."""
    edited = {k[0] for k in as_map(load(CFG["corrections"]))}
    return jsonify([
        {
            "video_id": r["video_id"],
            "id": r.get("id", ""),
            "title": r.get("titles", ""),
            "has_text": bool(clean(r.get("text"))),
            "edited": r["video_id"] in edited,
        }
        for r in rows()
    ])


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

    results = {}
    for field, value in payload["fields"].items():
        if not isinstance(value, str):
            return jsonify({"error": f"{field}: expected a string"}), 400
        results[field] = record(
            CFG["corrections"], CFG["backups"], video_id, field,
            clean(row.get(field)), value,
        )["status"]

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
