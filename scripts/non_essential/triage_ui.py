"""
Local triage page for new candidate sketches (plan step A6,
docs/superpowers/plans/2026-11-03-extend-archive.md).

One item per cluster of copies of the same recording, from data/candidates/matches.csv:
every `new` and `new*` cluster, plus a seeded sample of 30 `have` verdicts to spot-check
the engine. The chosen copy (A5) plays in a YouTube embed, which also proves it embeds;
the alternates are listed and can be picked instead.

Each save APPENDS a row to data/candidates/decisions.csv (the latest row per cluster
wins), so closing the tab never loses work. Binds to 127.0.0.1 only.

Usage:
  uv run --group review python scripts/non_essential/triage_ui.py      # then open http://127.0.0.1:5056
"""

from __future__ import annotations

import argparse
import csv
import logging
import random
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request

ROOT = Path(__file__).resolve().parents[2]
CAND = ROOT / "data" / "candidates"
DECISIONS = CAND / "decisions.csv"   # --decisions overrides it (tests write elsewhere)
FIELDS = ["decided_at", "cluster_id", "canonical_video_id", "scope", "shape", "already_in_archive",
          "archive_id_note", "bad_copies", "title_needs_curation", "notes"]
SCOPES = {"haghordum", "multer", "kaset", "out_of_scope", "not_kargin"}
SHAPES = {"one_sketch", "compilation", "fragment"}   # fragment: a piece of a sketch, a lead for a full copy
SPOTCHECK_N = 30
MAX_NOTE = 5000         # longer is refused with a 400, never silently cut
MAX_ARCHIVE_NOTE = 500
_WRITE_LOCK = threading.Lock()   # overlapping saves must not interleave appends (lost a row in review)

app = Flask(__name__, template_folder=str(ROOT / "scripts" / "review_templates"))
log = logging.getLogger("triage_ui")


def latest_decisions() -> dict[str, dict]:
    if not DECISIONS.exists():
        return {}
    return {r["cluster_id"]: r for r in csv.DictReader(open(DECISIONS, encoding="utf-8"))}


_CACHE: dict = {"mtime": None, "items": []}


def _build_items() -> list[dict]:
    """Clusters to triage, built once per version of matches.csv (plain Python: pandas
    per-group overhead made this 5.5 s, run on every save)."""
    rows = list(csv.DictReader(open(CAND / "matches.csv", encoding="utf-8")))
    by: dict[str, list[dict]] = {}
    for r in rows:
        by.setdefault(r["cluster_id"], []).append(r)
    items = []
    for cid, members in by.items():
        verdicts = {m["verdict"] for m in members}
        if verdicts & {"new", "new*"}:
            items.append((cid, "new*" if "new*" in verdicts else "new", members))
    # Spot-checks come only from clusters not already queued (a new* cluster also has a
    # `have` member; sampling it again would queue it twice with conflicting defaults).
    queued = {cid for cid, _, _ in items}
    have_ids = sorted({r["cluster_id"] for r in rows if r["verdict"] == "have"} - queued)
    rng = random.Random(509)
    for cid in rng.sample(have_ids, min(SPOTCHECK_N, len(have_ids))):
        items.append((cid, "spotcheck_have", by[cid]))
    out = []
    for cid, kind, members in items:
        members = sorted(members, key=lambda m: (m["role"] != "canonical", m["video_id"]))
        out.append({"cluster_id": cid, "kind": kind, "members": members, "size": len(members),
                    "official": any(m["source"] == "kargintv" for m in members)})
    # Official uploads first, then the most-copied (popular) sketches, then the rest.
    out.sort(key=lambda x: (x["kind"] == "spotcheck_have", not x["official"], -x["size"], x["cluster_id"]))
    return out


def queue() -> list[dict]:
    """The cached clusters plus the CURRENT decisions (re-read per request: cheap, and the
    one thing that changes while the page is open)."""
    mtime = (CAND / "matches.csv").stat().st_mtime
    if _CACHE["mtime"] != mtime:
        _CACHE["items"], _CACHE["mtime"] = _build_items(), mtime
    done = latest_decisions()
    return [{**x, "decided": x["cluster_id"] in done, "decision": done.get(x["cluster_id"])} for x in _CACHE["items"]]


@app.route("/")
def index():
    return render_template("triage.html")


@app.route("/api/queue")
def api_queue():
    return jsonify(queue())


@app.route("/api/decide/<cluster_id>", methods=["POST"])
def api_decide(cluster_id: str):
    # JSON only (no force=True): a text/plain cross-site POST from another page in the
    # browser must not be able to record decisions.
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        abort(400, "body must be a JSON object sent as application/json")
    known = {x["cluster_id"]: x for x in queue()}
    if cluster_id not in known:
        abort(404, f"unknown cluster {cluster_id}")
    members = {x["video_id"] for x in known[cluster_id]["members"]}
    if d.get("canonical_video_id") not in members:
        abort(400, "canonical_video_id is not a member of this cluster")
    if d.get("scope") not in SCOPES:
        abort(400, f"scope must be one of {sorted(SCOPES)}")
    if d.get("shape") not in SHAPES:
        abort(400, f"shape must be one of {sorted(SHAPES)}")
    bad_in = d.get("bad_copies", [])
    if not isinstance(bad_in, list) or not all(isinstance(v, str) for v in bad_in):
        abort(400, "bad_copies must be a list of video ids")
    unknown = [v for v in bad_in if v not in members]
    if unknown:
        abort(400, f"bad_copies holds ids that are not in this cluster: {unknown[:5]}")
    if d["canonical_video_id"] in bad_in:
        abort(400, "the chosen copy is also marked bad; pick another copy or un-mark it")
    for flag in ("already_in_archive", "title_needs_curation"):
        if not isinstance(d.get(flag, False), bool):
            abort(400, f"{flag} must be true or false")
    notes, archnote = d.get("notes", ""), d.get("archive_id_note", "")
    if not isinstance(notes, str) or not isinstance(archnote, str):
        abort(400, "notes and archive_id_note must be strings")
    if len(notes) > MAX_NOTE or len(archnote) > MAX_ARCHIVE_NOTE:
        abort(400, f"notes over {MAX_NOTE} or archive note over {MAX_ARCHIVE_NOTE} characters; shorten it")
    row = {"decided_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "cluster_id": cluster_id,
           "canonical_video_id": d["canonical_video_id"], "scope": d["scope"], "shape": d["shape"],
           "already_in_archive": "yes" if d.get("already_in_archive", False) else "no",
           "archive_id_note": archnote, "bad_copies": ";".join(bad_in),
           "title_needs_curation": "yes" if d.get("title_needs_curation", False) else "no",
           "notes": notes}
    with _WRITE_LOCK:
        new_file = not DECISIONS.exists()
        with open(DECISIONS, "a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS)
            if new_file:
                w.writeheader()
            w.writerow(row)
    log.info(f"decided {cluster_id}: {row['scope']}/{row['shape']} canonical {row['canonical_video_id']}")
    return jsonify({"ok": True})


def main() -> int:
    global DECISIONS
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--decisions", type=Path, default=DECISIONS)
    ap.add_argument("--port", type=int, default=5056)
    args = ap.parse_args()
    DECISIONS = args.decisions
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(),
                                  logging.FileHandler(ROOT / "logs" / "triage_ui.log", encoding="utf-8")])
    if not (CAND / "matches.csv").exists():
        raise FileNotFoundError("data/candidates/matches.csv missing: run match_candidates.py first")
    q = queue()
    log.info(f"{len(q)} clusters to triage ({sum(x['decided'] for x in q)} already decided); "
             f"open http://127.0.0.1:{args.port}  (decisions -> {DECISIONS})")
    app.run(host="127.0.0.1", port=args.port, debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
