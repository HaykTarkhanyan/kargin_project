"""Throwaway (Phase 0.2): score audfprint2 on the ground truth.

Run with the afp-venv python. Stage 1 matches every ground-truth clip against the
archive index and saves every hit to probe_results.json (artifact of record). Stage 2
derives the threshold from the negatives and reports recall per kind.
Usage: python p0_probe_audfprint.py <p0 dir> [--score-only]
Runtime: ~0.1-0.2x real time per query, ~5-10 min for 128 clips (guess).
"""
import csv
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

P0 = Path(sys.argv[1])
SCORE_ONLY = "--score-only" in sys.argv
VID = re.compile(r"([A-Za-z0-9_-]{11})\.[^.]+$")
OFFSET_TOL = 1.0
gt = list(csv.DictReader(open(P0 / "groundtruth.csv", encoding="utf-8")))

if not SCORE_ONLY:
    from audfprint2 import cli
    from audfprint2.core import hash_table

    t0 = time.time()
    ht = hash_table.HashTable(str(P0 / "archive.pklz"))
    print(f"index loaded: {len(ht.names)} files, {time.time() - t0:.0f}s", flush=True)
    an = cli.setup_analyzer(density=20.0, is_match=True, pks_per_frame=5, fanout=3, freq_sd=30.0,
                            shifts=0, samplerate=11025, continue_on_error=False, ffmpeg_path=None)
    ma = cli.setup_matcher(match_win=2, search_depth=100, min_count=3, max_matches=10, exact_count=False,
                           find_time_range=True, time_quantile=0.05, sortbytime=False,
                           illustrate=False, illustrate_hpf=False)
    t_hop = an.n_hop / an.target_sr
    out = []
    for i, row in enumerate(gt, 1):
        q0 = time.time()
        rslts, dur, nhash = ma.match_file(an, ht, str(P0 / "clips" / row["clip"]))
        hits = []
        for (hid, n_al, align, n_raw, rank, tmin, tmax) in rslts:
            m = VID.search(str(ht.names[hid]))
            hits.append(dict(ref=m.group(1) if m else str(ht.names[hid]), aligned=int(n_al), raw=int(n_raw),
                             offset_sec=round(float(align) * t_hop, 2),
                             q_start=round(float(tmin) * t_hop, 1), q_end=round(float(tmax) * t_hop, 1)))
        out.append({**row, "query_hashes": int(nhash), "query_dur": round(float(dur), 1),
                    "match_sec": round(time.time() - q0, 2), "hits": hits})
        el = time.time() - t0
        print(f"[{i}/{len(gt)}] {row['kind']:16s} top={hits[0]['aligned'] if hits else 0:4d} "
              f"({el:.0f}s elapsed, ~{el / i * (len(gt) - i):.0f}s left)", flush=True)
    (P0 / "probe_results.json").write_text(json.dumps(out, indent=1), encoding="utf-8")

res = json.loads((P0 / "probe_results.json").read_text(encoding="utf-8"))


def found(r, thresh):
    """True if the expected ref is among hits at/above thresh (offset checked when known)."""
    for h in r["hits"]:
        if h["aligned"] < thresh or h["ref"] != r["expect_ref"]:
            continue
        if r["expect_offset"] and abs(h["offset_sec"] - float(r["expect_offset"])) > OFFSET_TOL:
            continue
        return True
    return False


def best_wrong(r):
    """Highest aligned count of any hit that is NOT a right answer (self-match of the query counts as right)."""
    right = {r["expect_ref"], r["source"]} - {""}
    return max([h["aligned"] for h in r["hits"] if h["ref"] not in right] or [0])


neg = [r for r in res if r["kind"].startswith("neg_")]
pos = [r for r in res if not r["kind"].startswith("neg_")]
neg_max = max(max([h["aligned"] for h in r["hits"]] or [0]) for r in neg)
wrong_max = max(best_wrong(r) for r in pos)
thresh = max(neg_max, wrong_max) + 1
print(f"\nnegatives: highest count on any hit = {neg_max}; wrong refs on positives: highest = {wrong_max}")
print(f"threshold (one above both) = {thresh}\n")
by = defaultdict(list)
for r in pos:
    by[r["kind"]].append(r)
for kind, rs in by.items():
    ok = sum(found(r, thresh) for r in rs)
    tops = sorted((max([h["aligned"] for h in r["hits"] if h["ref"] == r["expect_ref"]] or [0]) for r in rs))
    print(f"{kind:16s} {ok:3d}/{len(rs)} found   right-ref counts min/median: {tops[0]}/{tops[len(tops) // 2]}")
    for r in rs:
        if not found(r, thresh):
            right = [h for h in r["hits"] if h["ref"] == r["expect_ref"]]
            print(f"   MISS {r['clip']}: expect {r['expect_ref']} @ {r['expect_offset'] or '?'}; "
                  f"right-ref hits {[(h['aligned'], h['offset_sec']) for h in right][:3]}; top {r['hits'][:1]}")
print(f"\nmean match time per clip: {sum(r['match_sec'] for r in res) / len(res):.2f}s")
