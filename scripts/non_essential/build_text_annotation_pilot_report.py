"""
Build an HTML side-by-side report comparing the two pilot models' text
annotations (flash3 vs flash38) from data/text_annotations_pilot/*.json,
plus spend totals from data/gemini_spend_ledger.jsonl.

Derived entirely from saved JSON - rerunning this never re-calls the API.

Usage:
  uv run python scripts/non_essential/build_text_annotation_pilot_report.py
"""

from __future__ import annotations

import html
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PILOT_DIR = ROOT / "data" / "text_annotations_pilot"
PILOT_V2_DIR = ROOT / "data" / "text_annotations_pilot_v2"
PILOT_V3_DIR = ROOT / "data" / "text_annotations_pilot_v3"
LEDGER_PATH = ROOT / "data" / "gemini_spend_ledger.jsonl"
OUT_PATH = PILOT_DIR / "report.html"
# (dir, tag suffix appended to model_short) pairs to load
PILOT_DIRS = [(PILOT_DIR, ""), (PILOT_V2_DIR, "-v2"), (PILOT_V3_DIR, "-v3")]
MODELS = ["flash3-nothink-v2", "flash3-nothink-v3"]


def setup_logging() -> None:
    logs_dir = ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(logs_dir / "build_text_annotation_pilot_report.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def load_pilot() -> dict[int, dict[str, dict]]:
    by_seq: dict[int, dict[str, dict]] = defaultdict(dict)
    for pilot_dir, suffix in PILOT_DIRS:
        for path in sorted(pilot_dir.glob("*__*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            by_seq[data["seq"]][data["model_short"] + suffix] = data
    if not by_seq:
        raise RuntimeError(f"no pilot outputs found in {[d for d, _ in PILOT_DIRS]}")
    return dict(sorted(by_seq.items()))


def spend_summary() -> tuple[dict[str, dict], float]:
    per_model: dict[str, dict] = defaultdict(lambda: {"calls": 0, "in": 0, "out": 0, "usd": 0.0})
    for line in LEDGER_PATH.read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        m = per_model[e["model"]]
        m["calls"] += 1
        m["in"] += e["prompt_tokens"]
        m["out"] += e["output_tokens"] + e["thoughts_tokens"]
        m["usd"] += e["cost_usd"]
    total = sum(m["usd"] for m in per_model.values())
    return dict(per_model), total


def esc(s: object) -> str:
    return html.escape(str(s))


def annotation_cell(d: dict) -> str:
    rows = []
    for key, val in d["annotation"].items():
        if isinstance(val, list):
            joiner = "<br>" if key == "catchphrases" else ", "
            rendered = joiner.join(esc(v) for v in val) or "<i>none</i>"
        else:
            rendered = esc(val)
        rows.append((key, rendered))
    if d.get("prompt_tokens") is not None:
        rows.append(("tokens / cost",
                     f"{d['prompt_tokens']}+{d['output_tokens']}(+{d['thoughts_tokens']} think) / ${d['cost_usd']:.4f}"))
    return "".join(f"<p><b>{esc(k)}:</b> {v}</p>" for k, v in rows)


def main() -> None:
    setup_logging()
    by_seq = load_pilot()
    per_model, total = spend_summary()

    spend_rows = "".join(
        f"<tr><td>{esc(m)}</td><td>{v['calls']}</td><td>{v['in']:,}</td>"
        f"<td>{v['out']:,}</td><td>${v['usd']:.4f}</td></tr>"
        for m, v in per_model.items()
    )

    cards = []
    for seq, models in by_seq.items():
        any_d = next(iter(models.values()))
        src = any_d["input_sources"]
        tr = src["transcript"] or "none"
        cols = "".join(
            f"<td class='model'><h3>{esc(tag)} <small>({esc(models[tag]['model'])})</small></h3>"
            f"{annotation_cell(models[tag])}</td>"
            if tag in models else "<td class='model'><i>missing</i></td>"
            for tag in MODELS
        )
        cards.append(
            f"<h2>seq {seq}: {esc(any_d['title'])}</h2>"
            f"<p class='meta'>video={esc(any_d['video_id'])} | transcript={esc(tr)} | "
            f"curated text={'yes' if src['text'] else 'no'} | "
            f"text_common={'yes' if src['text_common'] else 'no'} | input {any_d['input_chars']:,} chars</p>"
            f"<table class='cmp'><tr>{cols}</tr></table>"
        )

    OUT_PATH.write_text(
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>Text annotation pilot</title><style>"
        "body{font-family:Segoe UI,sans-serif;max-width:1200px;margin:2em auto;padding:0 1em;color:#222}"
        "table{border-collapse:collapse;width:100%}"
        "td,th{border:1px solid #ccc;padding:.6em;vertical-align:top;text-align:left}"
        f"table.cmp{{table-layout:fixed}}table.cmp td.model{{width:{100 // len(MODELS)}%}}"
        ".meta{color:#666}h2{margin-top:2em;border-top:3px solid #D90012;padding-top:1em}"
        "h3 small{color:#888;font-weight:normal}p{margin:.35em 0}"
        "</style></head><body>"
        f"<h1>Text annotation pilot: {' vs '.join(MODELS)}</h1>"
        f"<p>{len(by_seq)} sketches, side by side. Derived from data/text_annotations_pilot/*.json.</p>"
        "<h2>Spend (all Gemini extraction calls so far, from data/gemini_spend_ledger.jsonl)</h2>"
        "<table><tr><th>model</th><th>calls</th><th>tokens in</th><th>tokens out (incl. thinking)</th><th>cost</th></tr>"
        f"{spend_rows}<tr><td colspan='4'><b>total</b></td><td><b>${total:.4f}</b></td></tr></table>"
        + "".join(cards) + "</body></html>",
        encoding="utf-8",
    )
    logging.info(f"report written: {OUT_PATH} ({len(by_seq)} sketches, total spend ${total:.4f})")


if __name__ == "__main__":
    main()
