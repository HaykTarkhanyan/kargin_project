"""Precompute EDA aggregates for the Stats page. Pure functions over sketch dicts."""
import collections
import itertools
import re

_WORD = re.compile(r"[Ա-և]+")
# Real Armenian case endings (validated): keep tight to avoid over-matching short names.
ACTOR_SUFFIXES = ("", "ին", "ի", "ից", "ով", "ում", "ը", "ն", "ներ", "ների", "ներին")
_STOP = set("ու և որ ա ես դու էս էն ինչ չի մի էլ ոնց հա բա դա ինձ քեզ նա մեր ձեր իր այ դե "
            "եմ ենք են եք ին ից ում էր հետ դուք մենք համար".split())


def _dialogue(s):
    return f"{s.get('text','')} {s.get('textCommon','')}"


def co_occurrence(sketches, top=7):
    counts = collections.Counter(a for s in sketches for a in set(s["actors"]))
    actors = [a for a, _ in counts.most_common(top)]
    idx = {a: i for i, a in enumerate(actors)}
    m = [[0]*len(actors) for _ in actors]
    for s in sketches:
        present = [a for a in set(s["actors"]) if a in idx]
        for a, b in itertools.combinations(present, 2):
            m[idx[a]][idx[b]] += 1
            m[idx[b]][idx[a]] += 1
    return actors, m


def word_counts(sketches, min_len=4, top=18):
    wc = collections.Counter()
    for s in sketches:
        for w in _WORD.findall(_dialogue(s)):
            w = w.lower()
            if len(w) >= min_len and w not in _STOP:
                wc[w] += 1
    return wc.most_common(top)


def bigram_counts(sketches, top=12):
    bg = collections.Counter()
    for s in sketches:
        toks = [w.lower() for w in _WORD.findall(_dialogue(s)) if len(w) >= 2]
        for a, b in zip(toks, toks[1:]):
            if a not in _STOP and b not in _STOP and len(a) >= 3 and len(b) >= 3:
                bg[a + " " + b] += 1
    return bg.most_common(top)


def composition(sketches):
    c = collections.Counter()
    for s in sketches:
        a = set(s["actors"])
        if not a:
            c["uncurated"] += 1
        elif a == {"Հայկո", "Մկո"}:
            c["duo"] += 1
        elif len(a) == 1:
            c["solo"] += 1
        else:
            c["ensemble"] += 1
    return dict(c)


def name_mentions(name, sketches):
    """Declension-aware: a word equals name, or name + a known suffix. NOT raw substring."""
    n = name.lower()
    count = 0
    for s in sketches:
        for w in _WORD.findall(_dialogue(s)):
            wl = w.lower()
            if wl == n or (wl.startswith(n) and wl[len(n):] in ACTOR_SUFFIXES):
                count += 1
                break
    return count


def _avg(views):
    return round(sum(views) / len(views)) if views else 0


def build_stats(sketches):
    n = len(sketches)
    views = [s["viewCount"] or 0 for s in sketches]
    secs = sum(s["durationSec"] or 0 for s in sketches)
    by_actor_n = collections.Counter(a for s in sketches for a in set(s["actors"]))
    by_actor_v = collections.defaultdict(list)
    for s in sketches:
        for a in set(s["actors"]):
            by_actor_v[a].append(s["viewCount"] or 0)
    loc_n = collections.Counter(s["location"] for s in sketches)
    loc_v = collections.defaultdict(list)
    for s in sketches:
        loc_v[s["location"]].append(s["viewCount"] or 0)
    dur = collections.defaultdict(list)
    for s in sketches:
        mnt = (s["durationSec"] or 0) / 60
        key = "<2ր" if mnt < 2 else "2-3ր" if mnt < 3 else "3-4ր" if mnt < 4 else "4-5ր" if mnt < 5 else "5ր+"
        dur[key].append(s["viewCount"] or 0)
    dur_order = ["<2ր", "2-3ր", "3-4ր", "4-5ր", "5ր+"]
    hist = collections.Counter()
    for v in views:
        k = "<250K" if v < 250e3 else "250-500K" if v < 500e3 else "500K-1M" if v < 1e6 else "1-2M" if v < 2e6 else "2M+"
        hist[k] += 1
    hist_order = ["<250K", "250-500K", "500K-1M", "1-2M", "2M+"]
    with_seq = sorted(((s["seq"], s["viewCount"] or 0) for s in sketches if s["seq"]))
    seq_bins = []
    if with_seq:
        size = max(1, len(with_seq) // 8)
        for i in range(0, len(with_seq), size):
            part = with_seq[i:i+size]
            seq_bins.append({"label": f"{part[0][0]}-{part[-1][0]}",
                             "avgViews": _avg([p[1] for p in part])})
    by_len = sorted(sketches, key=lambda s: s["durationSec"] or 0)
    actors_co, matrix = co_occurrence(sketches)
    # name suggestions: top dialogue-mentioned given names from a candidate pool
    candidates = ["Անի", "Արմեն", "Վարդան", "Գագ", "Սաքո", "Գագո", "Համո", "Գևորգ", "Սուրեն"]
    name_sugg = sorted(({"name": c, "n": name_mentions(c, sketches)} for c in candidates),
                       key=lambda x: -x["n"])
    return {
        "totals": {"sketches": n, "hours": round(secs/3600, 1), "views": sum(views),
                   "actors": len(by_actor_n), "from": min(s["uploadDate"] for s in sketches if s["uploadDate"]),
                   "to": max(s["uploadDate"] for s in sketches if s["uploadDate"])},
        "actorsByCount": [{"name": a, "n": c} for a, c in by_actor_n.most_common(8)],
        "actorsAvgViews": sorted(({"name": a, "n": len(v), "avgViews": _avg(v)}
                                  for a, v in by_actor_v.items() if len(v) >= 8), key=lambda x: -x["avgViews"]),
        "locationByCount": [{"loc": l, "n": c} for l, c in loc_n.most_common(8)],
        "locationAvgViews": sorted(({"loc": l, "n": len(v), "avgViews": _avg(v)}
                                    for l, v in loc_v.items() if l != "Այլ"), key=lambda x: -x["avgViews"]),
        "durationBuckets": [{"bucket": k, "n": len(dur[k]), "avgViews": _avg(dur[k])} for k in dur_order if dur[k]],
        "topViewed": [{"seq": s["seq"], "id": s["id"], "title": s["title"], "views": s["viewCount"] or 0}
                      for s in sorted(sketches, key=lambda s: s["viewCount"] or 0, reverse=True)[:5]],
        "coOccurrence": {"actors": actors_co, "matrix": matrix},
        "topWords": [{"w": w, "n": c} for w, c in word_counts(sketches)],
        "topPhrases": [{"p": p, "n": c} for p, c in bigram_counts(sketches)],
        "composition": composition(sketches),
        "viewsHistogram": [{"bucket": k, "n": hist[k]} for k in hist_order],
        "viewsBySeq": seq_bins,
        "extremes": {"shortestSec": by_len[0]["durationSec"], "shortestSeq": by_len[0]["seq"],
                     "longestSec": by_len[-1]["durationSec"], "longestMin": round((by_len[-1]["durationSec"] or 0)/60, 1)},
        "nameSuggestions": [x for x in name_sugg if x["n"] > 0][:6],
    }
