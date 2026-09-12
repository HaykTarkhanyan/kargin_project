"""
Compare two embedding variants produced by scripts/embed_annotations.py
(e.g. `full` vs `stripped`) on the same validation metrics: duplicate-pair
recovery, topic agreement, score-distribution spread, and neighbour coverage.

Reads only saved artifacts - never calls the API.

Usage:
  uv run python scripts/non_essential/compare_embedding_variants.py [--a full] [--b stripped]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EMB = ROOT / "data" / "embeddings"
ANN = ROOT / "data" / "text_annotations"
DUP = ROOT / "data" / "duplicates.csv"


def load(variant: str):
    sfx = "" if variant == "full" else f"__{variant}"
    path = EMB / f"similarity_matrix{sfx}.npz"
    if not path.exists():
        raise RuntimeError(f"missing {path.name} - run embed_annotations.py --variant {variant}")
    d = np.load(path, allow_pickle=False)
    sim = d["similarity"].astype(np.float64)
    return sim, [str(x) for x in d["video_ids"]]


def jac(a, b) -> float:
    A, B = set(a), set(b)
    return len(A & B) / len(A | B) if (A | B) else 0.0


def report(variant: str, sim, ids, ann, dup_pairs) -> dict:
    n = len(ids)
    idx = {v: i for i, v in enumerate(ids)}
    finite = np.isfinite(sim)
    off = sim[finite & ~np.eye(n, dtype=bool)]
    masked = np.where(finite, sim, -np.inf)
    top1_idx = masked.argmax(axis=1)
    top1 = masked.max(axis=1)

    ranks = []
    for a, b in dup_pairs:
        if a in idx and b in idx:
            i, j = idx[a], idx[b]
            ranks.append(int((masked[i] > sim[i, j]).sum()) + 1)
    ranks = np.array(ranks)

    tj = np.mean([jac(ann[ids[i]]["topics"], ann[ids[top1_idx[i]]]["topics"]) for i in range(n)])
    rng = np.random.default_rng(509)
    rand = rng.integers(0, n, n)
    rj = np.mean([jac(ann[ids[i]]["topics"], ann[ids[rand[i]]]["topics"]) for i in range(n)])

    cov = {t: int(((masked >= t).sum(axis=1) > 0).sum()) for t in (0.85, 0.80, 0.75, 0.72)}
    return {
        "variant": variant, "bg_mean": off.mean(), "bg_sd": off.std(),
        "top1_mean": top1.mean(), "top1_sd": top1.std(),
        "sep_sd": (top1.mean() - off.mean()) / off.std(),
        "dup_rank1": int((ranks == 1).sum()), "dup_n": len(ranks),
        "topic_j": tj, "topic_lift": tj / max(rj, 1e-9),
        "cov": cov, "top1_idx": top1_idx,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default="full")
    ap.add_argument("--b", default="stripped")
    args = ap.parse_args()

    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(ROOT / "logs" / "compare_embedding_variants.log",
                                                      encoding="utf-8"),
                                  logging.StreamHandler(sys.stdout)])

    ann = {}
    for p in ANN.glob("*__*.json"):
        a = json.loads(p.read_text(encoding="utf-8"))
        ann[a["video_id"]] = {**a["annotation"], "seq": a["seq"]}
    dupdf = pd.read_csv(DUP)
    dup_pairs = [(r.video_id_a, r.video_id_b) for _, r in dupdf[dupdf.verdict == "duplicate"].iterrows()]

    simA, idsA = load(args.a)
    simB, idsB = load(args.b)
    if idsA != idsB:
        raise RuntimeError("variants have different id ordering - cannot compare")
    A = report(args.a, simA, idsA, ann, dup_pairs)
    B = report(args.b, simB, idsB, ann, dup_pairs)

    print(f"\n{'metric':38s} {A['variant']:>12s} {B['variant']:>12s}   delta")
    print("-" * 80)
    rows = [
        ("background mean (the floor)", "bg_mean", "{:.4f}", -1),
        ("background sd", "bg_sd", "{:.4f}", 0),
        ("top-1 mean", "top1_mean", "{:.4f}", 1),
        ("separation (sd above background)", "sep_sd", "{:.3f}", 1),
        ("topic Jaccard at rank 1", "topic_j", "{:.4f}", 1),
        ("topic lift vs random", "topic_lift", "{:.2f}x", 1),
    ]
    for label, key, fmt, better in rows:
        a, b = A[key], B[key]
        d = b - a
        arrow = "" if better == 0 else ("  better" if d * better > 0 else "  worse")
        print(f"{label:38s} {fmt.format(a):>12s} {fmt.format(b):>12s}  {d:+.4f}{arrow}")
    print(f"{'known duplicates ranked #1':38s} {A['dup_rank1']:>7d}/{A['dup_n']:<4d} "
          f"{B['dup_rank1']:>7d}/{B['dup_n']:<4d}")
    for t in (0.85, 0.80, 0.75, 0.72):
        print(f"{'sketches with a neighbour >= ' + f'{t:.2f}':38s} {A['cov'][t]:>12d} {B['cov'][t]:>12d}"
              f"  {B['cov'][t] - A['cov'][t]:+d}")
    changed = int((A["top1_idx"] != B["top1_idx"]).sum())
    print(f"\ntop-1 neighbour changed for {changed}/{len(idsA)} sketches ({changed/len(idsA):.1%})")

    print("\nexamples where the top-1 neighbour changed:")
    shown = 0
    for i in range(len(idsA)):
        if A["top1_idx"][i] != B["top1_idx"][i] and shown < 8:
            src = ann[idsA[i]]
            oa, ob = ann[idsA[A["top1_idx"][i]]], ann[idsA[B["top1_idx"][i]]]
            print(f"  [{src['seq']}] {src['title_en']} ({', '.join(src['topics'])})")
            print(f"      {args.a:9s} {simA[i, A['top1_idx'][i]]:.3f}  [{oa['seq']}] {oa['title_en']} ({', '.join(oa['topics'])})")
            print(f"      {args.b:9s} {simB[i, B['top1_idx'][i]]:.3f}  [{ob['seq']}] {ob['title_en']} ({', '.join(ob['topics'])})")
            shown += 1


if __name__ == "__main__":
    main()
