"""
Turn raw audio-match hits into a verdict per standalone candidate (plan step A4,
docs/superpowers/plans/2026-11-03-extend-archive.md).

Inputs (from scripts/audio_index.py):
  data/candidates/matches_archive.jsonl   each candidate's 90 s clip vs the archive index
  data/candidates/matches_self.jsonl      each candidate's clip vs an index of all candidate clips
  data/candidates/candidates.csv          the A1 list

Verdicts:
  have    matches an archive sketch at >= MATCH_DENSITY (archive id, offset, span recorded)
  multi   within its clip it matches two DIFFERENT archive sketches in non-overlapping
          stretches: a compilation in disguise, moved to the Phase M pool
  new     matches nothing in the archive
  new*    'new' but clustered with a 'have' candidate: probably a re-cut of a sketch we
          already have; flagged for the human triage (A6), not decided here
  gated_out  an unmarked title from a channel gate_unclear.py skipped (its unmarked uploads
          don't match the archive), and it didn't match either: kept out of the triage
  unavailable  the screening download failed: gone, private or sign-in only
          (candidates_failures.csv); can't be the archive's copy
  no_clip  not downloaded yet

Copies of the same recording among the candidates share a cluster_id (union-find over
candidate-vs-candidate hits). A hit on an archive compilation that overlaps a hit on a
plain sketch is the same audio (the compilation contains the sketch), so it never makes
a clip 'multi'.

Copy choice (plan step A5, Q8): within each cluster one member is `canonical`, the rest
are `alternate`. Rank: passes the hard requirements (data/candidates/status.csv: public,
embeddable, unblocked in AM/DE, not age-restricted), then official KarginTV before fan
copies, then HD before SD, then the channel likelier to keep it up (older channel, then
more uploads), then the earliest upload. Crop/mirror/watermark can't be judged here;
the A6 triage page has a "bad copy, use the next" button for that.

Writes data/candidates/matches.csv. Usage (~5 s):
  uv run python scripts/non_essential/match_candidates.py
"""

from __future__ import annotations

import json
import logging
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from audio_index import MATCH_DENSITY  # noqa: E402  (pure constant; no audfprint import)

CAND = ROOT / "data" / "candidates"
SPAN_OVERLAP = 0.5   # two hits are the same audio if their query spans overlap by half the shorter one
# Two candidate clips are copies only if the match covers at least this share of the
# querying clip. Shorter links are shared intros: one uploader opens every Kaset clip with
# the same ~25 s, which chained tapes 3, 4 and 5 into one "cluster" (links of 22-28 s at
# offset ~0, while the real copy pair in it shared 71 s). 12% of all 1,285 links were < 50%.
COPY_SHARE = 0.5


# A `have` needs the match to cover a real stretch of the clip, not just a jingle: a
# 16.5 s Kaset opener made U39YRsOOw2E "have" for an unrelated archive sketch (review).
HAVE_MIN_SPAN_SEC = 30.0

PERMANENT = ("not available", "private video", "video unavailable", "removed", "please sign in",
             "confirm your age", "account", "terminated", "copyright")


def is_permanent_failure(message: str) -> bool:
    """Gone, private, sign-in only or age-gated: a fact about the video. Anything else
    (ffmpeg exits, HTTP 403 mid-stream, timeouts) is transient and gets retried."""
    m = (message or "").lower()
    return any(k in m for k in PERMANENT)


def permanent_failures(fail_path: Path, have_clip: set[str]) -> set[str]:
    """Video ids whose LATEST screening attempt failed permanently and that have no clip."""
    if not fail_path.exists():
        return set()
    f = pd.read_csv(fail_path, dtype={"video_id": str}).sort_values("at")
    latest = f.groupby("video_id").tail(1)
    return {r.video_id for r in latest.itertuples() if is_permanent_failure(r.message) and r.video_id not in have_clip}


def is_have_hit(hit: dict, query_dur: float) -> bool:
    """A single stretch that is a match on its own (kept for tests and the single-stretch case)."""
    return (hit["density"] >= MATCH_DENSITY
            and (hit["q_end"] - hit["q_start"]) >= min(HAVE_MIN_SPAN_SEC, 0.5 * query_dur))


HAVE_COVER = 0.3   # distinct seconds of the SKETCH covered, as a share of the clip


def _union_len(intervals: list[tuple[float, float]]) -> float:
    total, end = 0.0, float("-inf")
    for a, b in sorted(intervals):
        if b <= end:
            continue
        total += b - max(a, end)
        end = b
    return total


def sketch_evidence(hits: list[dict], query_dur: float, canon: dict[str, str]) -> dict[str, dict]:
    """Per archive sketch (duplicates merged): every stretch of the clip that matched it, summed.

    Scoring each stretch alone missed montage shorts that cut one sketch into pieces: each
    piece scores under 2.0, together they are plainly that sketch (review 2026-11-03: 138
    `new` clips were such montages; "Տրիներ" is archive "Trener"). Coverage is measured on
    the SKETCH's own timeline (query time + offset), so a jingle repeated twice covers the
    same few seconds of the sketch once, and doesn't add up to a match.
    """
    by: dict[str, list[dict]] = {}
    for h in hits:
        by.setdefault(canon.get(h["ref"], h["ref"]), []).append(h)
    out = {}
    for ref, hs in by.items():
        out[ref] = {
            "score": sum(h["aligned"] for h in hs) / max(query_dur, 1.0),
            "sketch_cover": _union_len([(h["q_start"] + h["offset_sec"], h["q_end"] + h["offset_sec"]) for h in hs]),
            "q_spans": [(h["q_start"], h["q_end"]) for h in hs],
            "n_stretches": len(hs),
            "best": max(hs, key=lambda h: h["aligned"]),
        }
    return out


def qualifies(ev: dict, query_dur: float) -> bool:
    return ev["score"] >= MATCH_DENSITY and ev["sketch_cover"] >= HAVE_COVER * query_dur


def matches_archive(row: dict, canon: dict[str, str]) -> bool:
    """Does this screening clip match some archive sketch (the per-sketch rule)?"""
    return any(qualifies(ev, row["query_dur"]) for ev in sketch_evidence(row["hits"], row["query_dur"], canon).values())


def duplicate_canon(k: pd.DataFrame) -> dict[str, str]:
    """Archive video id -> one id for its duplicate group (kargin_eng.csv duplicate_of), so a
    sketch uploaded twice counts as one sketch, not two (review: 82tNQFueJfU nearly 'multi')."""
    import re
    vid_re = re.compile(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})")
    canon: dict[str, str] = {}
    for vid, dup in zip(k.index, k["duplicate_of"].fillna("")):
        group = sorted({vid, *vid_re.findall(dup)}, key=lambda v: (k.at[v, "id"] if v in k.index else "999", v))
        for g in group:
            canon[g] = min(canon.get(g, group[0]), group[0])
    return canon


def is_copy_link(hit: dict, query_dur: float) -> bool:
    return hit["density"] >= MATCH_DENSITY and (hit["q_end"] - hit["q_start"]) >= COPY_SHARE * query_dur

log = logging.getLogger("match_candidates")


def read_jsonl(path: Path) -> dict[str, dict]:
    if not path.exists():
        raise FileNotFoundError(f"{path} missing: run scripts/audio_index.py match first")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return {r["video_id"]: r for r in rows}


def overlaps(a: dict, b: dict) -> bool:
    lo, hi = max(a["q_start"], b["q_start"]), min(a["q_end"], b["q_end"])
    shorter = min(a["q_end"] - a["q_start"], b["q_end"] - b["q_start"])
    return shorter > 0 and (hi - lo) >= SPAN_OVERLAP * shorter


def distinct_stretches(hits: list[dict]) -> list[list[dict]]:
    """Group hits whose query spans overlap: each group is one stretch of audio."""
    groups: list[list[dict]] = []
    for h in sorted(hits, key=lambda x: -x["density"]):
        for g in groups:
            if any(overlaps(h, o) for o in g):
                g.append(h)
                break
        else:
            groups.append([h])
    return groups


def canonical_order(members: list[dict]) -> list[dict]:
    """Q8 ranking, best first. Each member needs: status, source, definition,
    channel_created (YYYYMMDD or ''), channel_videos (int), upload_date (YYYYMMDD)."""
    def key(m: dict):
        return (
            m.get("status") != "ok",
            m.get("source") != "kargintv",
            m.get("definition") != "hd",
            str(m.get("channel_created") or "99999999"),
            -int(m.get("channel_videos") or 0),
            str(m.get("upload_date") or "99999999"),
            m["video_id"],
        )
    return sorted(members, key=key)


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def main() -> None:
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(),
                  logging.FileHandler(ROOT / "logs" / "match_candidates.log", encoding="utf-8")],
    )
    t0 = time.time()
    cand = pd.read_csv(CAND / "candidates.csv", dtype={"video_id": str})
    arch = read_jsonl(CAND / "matches_archive.jsonl")
    selfm = read_jsonl(CAND / "matches_self.jsonl")
    k = pd.read_csv(ROOT / "kargin_eng.csv", dtype={"id": str, "video_id": str}).set_index("video_id")
    meta = pd.read_csv(ROOT / "data" / "youtube_metadata.csv", dtype={"video_id": str}).set_index("video_id")
    comps = set(pd.read_csv(ROOT / "data" / "compilations" / "pool.csv", dtype={"video_id": str})
                .query("source == 'archive'")["video_id"])
    gate_path = CAND / "unclear_gate.csv"
    if (cand.series == "unclear").any() and not gate_path.exists():
        raise FileNotFoundError(f"{gate_path} missing: run gate_unclear.py decide before judging unmarked titles")
    # keyed by channel_id: titles aren't unique ("ԿԱՐԳԻՆ BOT" is two channels)
    gate = (pd.read_csv(gate_path, dtype=str).set_index("channel_id")["decision"].to_dict() if gate_path.exists() else {})
    failed = permanent_failures(CAND / "candidates_failures.csv", set(arch))
    canon = duplicate_canon(k)
    missing = sorted(set(cand.video_id) - set(arch))
    if missing:
        log.warning(f"{len(missing)} candidates have no archive match row (no screening clip yet?): {missing[:8]}")

    uf = UnionFind()
    for vid, r in selfm.items():
        uf.find(vid)
        for h in r["hits"]:
            if h["ref"] != vid and is_copy_link(h, r["query_dur"]):
                uf.union(vid, h["ref"])

    rows = []
    for _, c in cand.iterrows():
        r = arch.get(c.video_id)
        base = {**c.to_dict(), "cluster_id": uf.find(c.video_id)}
        gated = c.series == "unclear" and gate.get(c.channel_id) == "skip"
        if r is None:
            rows.append({**base, "verdict": "unavailable" if c.video_id in failed
                         else "gated_out" if gated else "no_clip"})
            continue
        ev = {ref: e for ref, e in sketch_evidence(r["hits"], r["query_dur"], canon).items() if qualifies(e, r["query_dur"])}
        # Compilation refs only stand in when no plain sketch qualified (a clip of sketch X
        # also matches every archive compilation containing X).
        plain = {ref: e for ref, e in ev.items() if ref not in comps}
        chosen = plain or ev
        # multi: two DIFFERENT plain sketches on stretches of the clip that don't overlap
        heads = sorted(chosen.items(), key=lambda kv: -kv[1]["score"])
        distinct = []
        for ref, e in heads:
            span = (min(a for a, _ in e["q_spans"]), max(b for _, b in e["q_spans"]))
            if all(not overlaps({"q_start": span[0], "q_end": span[1]}, {"q_start": s[0], "q_end": s[1]})
                   for _, s in distinct):
                distinct.append((ref, span))
        if plain and len(distinct) >= 2:
            verdict = "multi"
        elif heads:
            verdict = "have"
        else:
            verdict = "gated_out" if gated else "new"
        top = {**heads[0][1]["best"], "ref": heads[0][0], "density": round(heads[0][1]["score"], 3)} if heads else None
        heads = [h for h, _ in distinct]
        rows.append({**base, "verdict": verdict,
                     "archive_ref": top["ref"] if top else "",
                     "archive_id": k.at[top["ref"], "id"] if top and top["ref"] in k.index else "",
                     "archive_title": meta.at[top["ref"], "title"] if top and top["ref"] in meta.index else "",
                     "offset_sec": top["offset_sec"] if top else "",
                     "density": top["density"] if top else (max([h["density"] for h in r["hits"]] or [0])),
                     "matched_span": f"{top['q_start']}-{top['q_end']}" if top else "",
                     "n_stretches": len(heads),
                     "clip_dur": r["query_dur"]})

    df = pd.DataFrame(rows)
    sizes = df.groupby("cluster_id").size()
    df["cluster_size"] = df["cluster_id"].map(sizes)
    have_clusters = set(df.loc[df.verdict == "have", "cluster_id"])
    df.loc[(df.verdict == "new") & df.cluster_id.isin(have_clusters), "verdict"] = "new*"

    status = pd.read_csv(CAND / "status.csv", dtype={"video_id": str}).set_index("video_id")
    chans = {c["channel_id"]: c for c in json.loads(
        (ROOT / "data" / "channel_scout" / "channels.json").read_text(encoding="utf-8"))}
    df["status"] = df.video_id.map(status["status"]).fillna("unknown")
    df["definition"] = df.video_id.map(status["definition"]).fillna("")
    df["channel_created"] = df.channel_id.map(lambda c: (chans.get(c) or {}).get("created") or "")
    df["channel_videos"] = df.channel_id.map(lambda c: (chans.get(c) or {}).get("video_count_reported") or 0)
    df["role"] = "alternate"
    for _, g in df.groupby("cluster_id"):
        best = canonical_order(g.to_dict("records"))[0]
        df.loc[df.video_id == best["video_id"], "role"] = "canonical"
    df.to_csv(CAND / "matches.csv", index=False, encoding="utf-8")
    log.info(f"canonical copies: {int((df.role == 'canonical').sum())} for {df.cluster_id.nunique()} clusters; "
             f"canonicals failing hard requirements: "
             f"{int(((df.role == 'canonical') & (df.status != 'ok')).sum())} (no playable copy in the cluster)")

    log.info(f"verdicts: {dict(Counter(df.verdict))}")
    new = df[df.verdict == "new"]
    log.info(f"'new' candidates: {len(new)} in {new.cluster_id.nunique()} clusters "
             f"(by series {dict(Counter(new.drop_duplicates('cluster_id').series))})")
    log.info(f"archive sketches matched by some candidate: {df.loc[df.verdict == 'have', 'archive_ref'].nunique()}")
    log.info(f"done in {time.time() - t0:.1f}s -> {CAND / 'matches.csv'}")


if __name__ == "__main__":
    main()
