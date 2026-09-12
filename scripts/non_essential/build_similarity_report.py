"""
HTML report over the embedding artifacts in data/embeddings/: validation stats
(including the audio-fingerprint duplicate cross-check) plus each sketch's
nearest neighbours, for eyeballing similarity quality.

Derived entirely from saved artifacts - never re-calls the API.

Usage:
  uv run python scripts/non_essential/build_similarity_report.py [--top-n 5]
"""

from __future__ import annotations

import argparse
import html
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EMB_DIR = ROOT / "data" / "embeddings"
ANN_DIR = ROOT / "data" / "text_annotations"
DUP_CSV = ROOT / "data" / "duplicates.csv"
OUT_PATH = EMB_DIR / "similarity_report.html"


def esc(s: object) -> str:
    return html.escape(str(s))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-n", type=int, default=5)
    args = parser.parse_args()

    logs = ROOT / "logs"
    logs.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(logs / "build_similarity_report.log", encoding="utf-8"),
                                  logging.StreamHandler(sys.stdout)])

    d = np.load(EMB_DIR / "similarity_matrix.npz", allow_pickle=False)
    sim = d["similarity"].astype(np.float64)
    ids = [str(x) for x in d["video_ids"]]
    idx = {v: i for i, v in enumerate(ids)}
    n = len(ids)

    meta: dict[str, dict] = {}
    for p in ANN_DIR.glob("*__*.json"):
        a = json.loads(p.read_text(encoding="utf-8"))
        meta[a["video_id"]] = {
            "seq": a["seq"], "model": a["model_short"],
            "title_en": a["annotation"]["title_en"], "title_hy": a["annotation"]["title_hy"],
            "topics": a["annotation"]["topics"], "summary": a["annotation"]["summary_en"],
        }

    off = sim[~np.eye(n, dtype=bool)]
    off = off[np.isfinite(off)]
    top1 = np.max(np.where(np.isfinite(sim), sim, -np.inf), axis=1)

    dup = pd.read_csv(DUP_CSV)
    strict = dup[dup.verdict == "duplicate"]
    ranks, dscores = [], []
    for _, r in strict.iterrows():
        if r.video_id_a in idx and r.video_id_b in idx:
            i, j = idx[r.video_id_a], idx[r.video_id_b]
            s = sim[i, j]
            dscores.append(s)
            row = np.where(np.isfinite(sim[i]), sim[i], -np.inf)
            ranks.append(int((row > s).sum()) + 1)
    ranks, dscores = np.array(ranks), np.array(dscores)

    stats = f"""
    <table>
      <tr><th>check</th><th>value</th><th>reading</th></tr>
      <tr><td>background similarity (all off-diagonal pairs)</td>
          <td>mean {off.mean():.3f}, sd {off.std():.3f}</td>
          <td>every doc is a Kargin sketch, so baseline is high</td></tr>
      <tr><td>top-1 neighbour score</td><td>mean {top1.mean():.3f}, sd {top1.std():.3f}</td>
          <td><b>{(top1.mean()-off.mean())/off.std():.2f} sd above background</b></td></tr>
      <tr><td>known duplicate pairs (audio fingerprint) ranked #1</td>
          <td><b>{int((ranks==1).sum())} / {len(ranks)}</b></td>
          <td>independent ground truth - the embedding never saw the audio</td></tr>
      <tr><td>cosine on those duplicate pairs</td>
          <td>mean {dscores.mean():.3f} (min {dscores.min():.3f})</td>
          <td>vs {off.mean():.3f} background</td></tr>
    </table>"""

    order = np.argsort(-np.where(np.isfinite(sim), sim, -np.inf), axis=1)[:, :args.top_n]
    blocks = []
    for i in np.argsort([meta[v]["seq"] for v in ids]):
        vid = ids[i]
        m = meta[vid]
        tag = "" if m["model"].startswith("flash") else f" <span class='badge'>{esc(m['model'])}</span>"
        rows = "".join(
            f"<tr><td class='score'>{sim[i, j]:.3f}</td>"
            f"<td>[{meta[ids[j]]['seq']}] <b>{esc(meta[ids[j]]['title_en'])}</b><br>"
            f"<span class='hy'>{esc(meta[ids[j]]['title_hy'])}</span><br>"
            f"<span class='top'>{esc(', '.join(meta[ids[j]]['topics']))}</span></td>"
            f"<td class='sum'>{esc(meta[ids[j]]['summary'])}</td></tr>"
            for j in order[i]
        )
        blocks.append(
            f"<h2>[{m['seq']}] {esc(m['title_en'])} <span class='hy'>/ {esc(m['title_hy'])}</span>{tag}</h2>"
            f"<p class='meta'>{esc(vid)} &middot; {esc(', '.join(m['topics']))}</p>"
            f"<p class='sum'>{esc(m['summary'])}</p>"
            f"<table class='nb'><tr><th>cos</th><th>neighbour</th><th>its summary</th></tr>{rows}</table>"
        )

    OUT_PATH.write_text(
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Sketch similarity</title><style>"
        "body{font-family:Segoe UI,sans-serif;max-width:1150px;margin:2em auto;padding:0 1em;color:#222}"
        "table{border-collapse:collapse;width:100%;margin:.5em 0}"
        "td,th{border:1px solid #ccc;padding:.5em;vertical-align:top;text-align:left;font-size:14px}"
        "table.nb{table-layout:fixed}table.nb td:nth-child(1){width:60px}table.nb td:nth-child(2){width:280px}"
        "h2{margin-top:2em;border-top:3px solid #0033A0;padding-top:.8em;font-size:18px}"
        ".hy{color:#666;font-weight:normal}.meta{color:#888;font-size:13px;margin:.2em 0}"
        ".sum{color:#333;font-size:13px}.score{font-weight:bold;color:#D90012}"
        ".top{color:#F2A800;font-size:12px}"
        ".badge{background:#0033A0;color:#fff;font-size:11px;padding:2px 6px;border-radius:3px}"
        "</style></head><body>"
        f"<h1>Sketch similarity - gemini-embedding-2</h1>"
        f"<p>{n} sketches, 3072-dim embeddings of <code>summary_detailed_en</code>, cosine similarity. "
        f"Rows tagged <span class='badge'>opus</span> were annotated by Claude after Gemini's content filter refused them.</p>"
        f"<h2 style='border:none'>Validation</h2>{stats}"
        + "".join(blocks) + "</body></html>",
        encoding="utf-8")
    logging.info(f"report written: {OUT_PATH} ({OUT_PATH.stat().st_size/1024/1024:.1f} MB)")


if __name__ == "__main__":
    main()
