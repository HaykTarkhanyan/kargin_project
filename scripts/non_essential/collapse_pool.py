"""
Collapse obvious copies in the multi-sketch pool before downloading full audio (plan
step M2). Only exact copies are merged here: Kaset tapes with the same tape number AND a
duration within DUR_TOL_SEC. Parts and clips of a tape (tape 4 has 19 entries from 78 s
to 4,528 s) are left alone; the audio match sorts those out after download.

One copy per group is chosen by the Q8 ranking (match_candidates.canonical_order): hard
requirements, official first, HD, older channel, more uploads, earliest upload.

Writes data/compilations/pool_groups.csv (every pool row with its group and role) and
data/compilations/pool_download_ids.txt (the rows to download: every non-archive row
that is its group's chosen copy). Usage (~2 s):
  uv run python scripts/non_essential/collapse_pool.py
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
COMP = ROOT / "data" / "compilations"
DUR_TOL_SEC = 10.0
TAPE = re.compile(r"(?:kaset|կասետ|кассет)\D{0,6}(\d{1,2})", re.I)

log = logging.getLogger("collapse_pool")


def groups_for(p: pd.DataFrame) -> pd.Series:
    """Group id per row: numbered Kaset tapes chained by duration within DUR_TOL_SEC; else its own id."""
    gid = p["video_id"].copy()
    tape = p["title"].fillna("").str.extract(TAPE)[0]
    for n, g in p[(p.series == "kaset") & tape.notna()].groupby(tape):
        g = g.sort_values("duration_sec")
        head, last = None, None
        for idx, r in g.iterrows():
            if head is None or r.duration_sec - last > DUR_TOL_SEC:
                head = f"kaset{n}_{int(r.duration_sec)}"
            gid.at[idx] = head
            last = r.duration_sec
    return gid


def main() -> None:
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(),
                                  logging.FileHandler(ROOT / "logs" / "collapse_pool.log", encoding="utf-8")])
    from match_candidates import canonical_order

    p = pd.read_csv(COMP / "pool.csv", dtype={"video_id": str})
    status = pd.read_csv(ROOT / "data" / "candidates" / "status.csv", dtype={"video_id": str}).set_index("video_id")
    # by channel_id: titles aren't unique ("ԿԱՐԳԻՆ BOT" is two channels; review finding 8)
    chans = {c["channel_id"]: c for c in json.loads((ROOT / "data" / "channel_scout" / "channels.json").read_text(encoding="utf-8"))}
    p["group_id"] = groups_for(p)
    p["status"] = p.video_id.map(status["status"]).fillna("archive")
    p["definition"] = p.video_id.map(status["definition"]).fillna("")
    p["channel_created"] = p.channel_id.map(lambda c: (chans.get(c) or {}).get("created") or "")
    p["channel_videos"] = p.channel_id.map(lambda c: (chans.get(c) or {}).get("video_count_reported") or 0)
    p["role"] = "copy"
    for _, g in p.groupby("group_id"):
        best = canonical_order(g.to_dict("records"))[0]
        p.loc[p.video_id == best["video_id"], "role"] = "chosen"
    p.to_csv(COMP / "pool_groups.csv", index=False, encoding="utf-8")
    # Pool videos are only MINED for audio (Q15), never shown on the site, so embedding and
    # AM blocks don't matter here: only whether this machine (in Germany) can download it.
    st = status.reindex(p.video_id)
    p["downloadable"] = ((st["privacy"].values == "public") & ~st["age_restricted"].fillna(True).astype(bool).values
                         & st["playable_DE"].fillna(False).astype(bool).values)
    dl = p[(p.role == "chosen") & (p.source != "archive") & p.downloadable]
    (COMP / "pool_download_ids.txt").write_text("\n".join(dl.video_id) + "\n", encoding="utf-8")
    merged = p[p.role == "copy"]
    log.info(f"pool {len(p)} rows -> {p.group_id.nunique()} groups; {len(merged)} copies merged "
             f"({round(merged.duration_sec.sum() / 60)} min not downloaded)")
    log.info(f"to download: {len(dl)} videos, {round(dl.duration_sec.sum() / 60)} min of audio "
             f"(~{dl.duration_sec.sum() / 60 * 0.36 / 1024:.1f} GB at 48 kbps); "
             f"not downloadable (gone, private, age-gated or blocked in DE): "
             f"{int(((p.role == 'chosen') & (p.source != 'archive') & ~p.downloadable).sum())}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
