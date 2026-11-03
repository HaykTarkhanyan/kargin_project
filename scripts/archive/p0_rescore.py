"""Throwaway: re-score the audfprint probe by hash DENSITY (aligned hashes per query second).

A hit counts as genuine if its ref is the expected one, a listed duplicates.csv partner, or
an archive compilation (verified above to contain the query). Everything else on a positive,
and every hit on a negative, is spurious. Reports the density gap and recall at a threshold.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

P0, ROOT = Path(sys.argv[1]), Path(sys.argv[2])
res = json.loads((P0 / "probe_results.json").read_text(encoding="utf-8"))
d = pd.read_csv(ROOT / "data" / "duplicates.csv")
partners = defaultdict(set)
for _, r in d.iterrows():
    partners[r.video_id_a].add(r.video_id_b)
    partners[r.video_id_b].add(r.video_id_a)
lag = {(r.video_id_a, r.video_id_b): r.lag_sec for _, r in d.iterrows()}
COMPS = {"Fyc5VWnAMog", "3UZOwmPovQ4", "mrIUW3fCUUo", "lO4fAllxmwc", "E0apclx3wqU", "L3CiQABljX8",
         "VFajwBRJxc4", "aOZ3vbc1iFA"}

genuine, spurious = [], []
for r in res:
    qd = r["query_dur"] or 60.0
    for h in r["hits"]:
        dens = h["aligned"] / qd
        if r["kind"].startswith("neg_"):
            spurious.append((dens, r["clip"], h))
            continue
        src, exp = r["source"], r["expect_ref"]
        ok = (h["ref"] in (src, exp) or h["ref"] in partners[src] or h["ref"] in partners[exp]
              or h["ref"] in COMPS or src in COMPS)
        (genuine if ok else spurious).append((dens, r["clip"], h))

sp_max = max(s[0] for s in spurious)
print(f"spurious hits: {len(spurious)}, highest density {sp_max:.2f}/s "
      f"({max(spurious, key=lambda s: s[0])[1]} -> {max(spurious, key=lambda s: s[0])[2]['ref']})")

# Recall on the expected answer only, by density threshold.
THRESH = 2.0
print(f"threshold used: {THRESH}/s  (spurious max {sp_max:.2f}/s)\n")
by = defaultdict(list)
for r in res:
    if r["kind"].startswith("neg_"):
        continue
    qd = r["query_dur"] or 60.0
    best = None
    for h in r["hits"]:
        if h["ref"] != r["expect_ref"]:
            continue
        if r["expect_offset"] and abs(h["offset_sec"] - float(r["expect_offset"])) > 1.0:
            continue
        best = max(best or 0, h["aligned"] / qd)
    by[r["kind"]].append(best or 0.0)
for kind, ds in by.items():
    ok = sum(x >= THRESH for x in ds)
    s = sorted(ds)
    print(f"{kind:16s} {ok:3d}/{len(ds)} found at >= {THRESH}/s   density min/median {s[0]:.2f}/{s[len(s) // 2]:.2f}")

# Offset check for known pairs against the 2026-08-01 cross-correlation lags.
print("\nknown pairs: engine offset vs duplicates.csv lag (|diff| should be < 1 s; sign convention may flip)")
worst = 0.0
for r in res:
    if not r["kind"].startswith("known_"):
        continue
    hs = [h for h in r["hits"] if h["ref"] == r["expect_ref"]]
    if not hs:
        continue
    h = max(hs, key=lambda x: x["aligned"])
    L = lag.get((r["expect_ref"], r["source"]), lag.get((r["source"], r["expect_ref"])))
    diff = min(abs(h["offset_sec"] - L), abs(h["offset_sec"] + L))
    worst = max(worst, diff)
print(f"  worst |offset - lag| over {sum(r['kind'].startswith('known_') for r in res)} pairs: {worst:.2f} s")

summary = {"spurious_max_density": round(sp_max, 3), "threshold": THRESH,
           "recall": {k: [sum(x >= THRESH for x in v), len(v)] for k, v in by.items()},
           "known_pair_worst_offset_error_sec": round(worst, 3)}
(P0 / "probe_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
print("\n", json.dumps(summary))
