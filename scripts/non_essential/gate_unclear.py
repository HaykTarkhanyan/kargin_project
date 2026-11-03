"""
Decide, per channel, whether its UNMARKED candidate titles are worth screening
(DECISIONS #22). A title with no Kargin series marker can't be judged from text, so the
channel's own track record decides: sample a few of its unmarked uploads, match them
against the archive, and keep the channel only if they match often enough.

  sample   writes data/candidates/unclear_sample_ids.txt: up to sample_size() unmarked
           uploads per channel (8, 16 or 24 by channel size; seed 509), preferring ones
           already on disk, so a re-run only ever adds to the earlier sample
  decide   reads data/candidates/matches_archive.jsonl and writes
           data/candidates/unclear_gate.csv, one row per channel with its evidence:
             keep    >= KEEP_MATCHES of the sample, and >= KEEP_RATE of it, match the
                     archive: screen them all
             triage  the channel's MARKED uploads are mostly Kaset, which can never
                     match a Haghordum-only archive; its sample goes to the owner
             skip    otherwise; recorded with the numbers, never silently dropped

Marked titles (Haghordum, Multer, Kaset) are never gated. Usage (~2 s each):
  uv run python scripts/non_essential/gate_unclear.py sample
  uv run python scripts/non_essential/screen_audio.py --set candidates --ids-file data/candidates/unclear_sample_ids.txt
  uv run --group match python scripts/audio_index.py match --index archive --queries data/candidates/audio --out data/candidates/matches_archive.jsonl
  uv run python scripts/non_essential/gate_unclear.py decide
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path

import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "scripts"))
from match_candidates import duplicate_canon, matches_archive  # noqa: E402
# (one failure rule and one match rule for both scripts: the first gate used its own
#  single-stretch rule and skipped Kargin Club at 4/21; per sketch it is 12/21)
CAND = ROOT / "data" / "candidates"
# Sample size grows with the channel: a skip on 8 samples is weak evidence when it drops
# hundreds of titles. A channel truly matching at Կարգին Shorts' 37% shows 0-1 of 8 about
# 1 time in 7 (0.625^8 + 8*0.375*0.625^7 = 0.135), which is what the first gate risked on
# Kargin Club (1/8, 212 titles).
def sample_size(n_unclear: int) -> int:
    return 24 if n_unclear >= 100 else 16 if n_unclear >= 20 else 8


KEEP_MATCHES = 2       # Haghordum-titled fan clips match ~52% of the time, other shows ~0%
KEEP_RATE = 0.2        # ...and at least this share of the sample (2/8 = 25% passes, 4/24 doesn't)
MATCH_DENSITY = 2.0    # same as scripts/audio_index.py
VIDEO_ID = re.compile(r"([A-Za-z0-9_-]{11})\.[^.]+$")

log = logging.getLogger("gate_unclear")


def on_disk() -> set[str]:
    folder = CAND / "audio"
    return {m.group(1) for p in folder.iterdir() if (m := VIDEO_ID.search(p.name)) and p.suffix != ".part"}


def sample(c: pd.DataFrame, earlier: list[str]) -> list[str]:
    """Append-only: keep every id sampled before, top each channel up to sample_size() from a
    seeded permutation of its other unmarked uploads. (Preferring clips already on disk, as
    the first version did, re-picked a different sample once a kept channel was fully
    downloaded: review finding 9.)"""
    keep = set(earlier)
    out = [v for v in earlier if v in set(c.video_id)]
    for _, g in c[c.series == "unclear"].groupby("channel_id"):
        have_n = int(g.video_id.isin(keep).sum())
        rest = g[~g.video_id.isin(keep)].sample(frac=1, random_state=509)
        out += rest.head(max(0, sample_size(len(g)) - have_n)).video_id.tolist()
    return out


def decide(c: pd.DataFrame) -> pd.DataFrame:
    path = CAND / "matches_archive.jsonl"
    hits = {r["video_id"]: r for r in map(json.loads, path.read_text(encoding="utf-8").splitlines()) if r}
    sampled = set((CAND / "unclear_sample_ids.txt").read_text(encoding="utf-8").split())
    marked = c[c.series != "unclear"].groupby("channel_id").series.value_counts().unstack(fill_value=0)
    # For the gate's EVIDENCE, a sampled clip whose latest download attempt failed (for any
    # reason, after the retry pass) is left out and counted; a sample never attempted at all
    # is a real gap and stops the run. (Verdicts use the stricter permanent-only rule.)
    fail_path = CAND / "candidates_failures.csv"
    failed = set(pd.read_csv(fail_path, dtype={"video_id": str}).video_id) - set(hits) if fail_path.exists() else set()
    k = pd.read_csv(ROOT / "kargin_eng.csv", dtype={"id": str, "video_id": str}).set_index("video_id")
    canon = duplicate_canon(k)
    rows = []
    for chid, g in c[c.series == "unclear"].groupby("channel_id"):
        ch = g.channel_title.iloc[0]
        s = g[g.video_id.isin(sampled)]
        # A sampled video that could not be downloaded (gone, private, sign-in only) is a
        # recorded fact in candidates_failures.csv, not a missing step: leave it out of
        # the evidence and count it. A clip that exists but was never matched IS a gap.
        unavailable = [v for v in s.video_id if v not in hits and v in failed]
        missing = [v for v in s.video_id if v not in hits and v not in failed]
        if missing:
            raise RuntimeError(f"{ch}: {len(missing)} sampled clips have no match row yet (download/match them first): "
                               f"{missing[:5]}")
        s = s[~s.video_id.isin(unavailable)]
        n_match = sum(matches_archive(hits[v], canon) for v in s.video_id)
        m = marked.loc[chid] if chid in marked.index else pd.Series(dtype=int)
        kaset_channel = int(m.get("kaset", 0)) > int(m.get("haghordum", 0))
        keep = n_match >= KEEP_MATCHES and n_match >= KEEP_RATE * max(len(s), 1)
        # no usable sample at all is no evidence: the owner sees it rather than a silent skip
        decision = "keep" if keep else "triage" if (kaset_channel or len(s) == 0) else "skip"
        rows.append({"channel_id": chid, "channel_title": ch, "unclear_rows": len(g), "sampled": len(s),
                     "sample_unavailable": len(unavailable), "sample_matched": n_match,
                     "marked_haghordum": int(m.get("haghordum", 0)), "marked_kaset": int(m.get("kaset", 0)),
                     "decision": decision})
    return pd.DataFrame(rows).sort_values(["decision", "unclear_rows"], ascending=[True, False])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["sample", "decide"])
    args = ap.parse_args()
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(),
                                  logging.FileHandler(ROOT / "logs" / "gate_unclear.log", encoding="utf-8")])
    c = pd.read_csv(CAND / "candidates.csv", dtype={"video_id": str})
    if args.mode == "sample":
        path = CAND / "unclear_sample_ids.txt"
        earlier = path.read_text(encoding="utf-8").split() if path.exists() else []
        ids = sample(c, earlier)
        (CAND / "unclear_sample_ids.txt").write_text("\n".join(ids) + "\n", encoding="utf-8")
        log.info(f"sampled {len(ids)} unmarked uploads from {c[c.series == 'unclear'].channel_title.nunique()} "
                 f"channels ({len(set(ids) & on_disk())} already on disk)")
    else:
        g = decide(c)
        g.to_csv(CAND / "unclear_gate.csv", index=False, encoding="utf-8")
        for d, sub in g.groupby("decision"):
            log.info(f"{d}: {len(sub)} channels, {int(sub.unclear_rows.sum())} unmarked rows")
        log.info(f"-> {CAND / 'unclear_gate.csv'}")


if __name__ == "__main__":
    main()
