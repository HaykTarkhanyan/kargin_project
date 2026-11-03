"""
Sort the channel-scout videos into standalone candidates, the multi-sketch pool, and
skips (plan step A1 + M1, docs/superpowers/plans/2026-11-03-extend-archive.md).

Reads data/channel_scout/videos.csv (scout_channels.py) and the archive's own
compilations flagged by the visual pass. No API calls, no downloads.

Writes:
  data/candidates/candidates.csv   standalone sketches, 60-480 s, in scope (Q5)
  data/compilations/pool.csv       compilations, episodes, tapes,
                                   and the archive's own flagged compilations
  data/candidates/skipped.csv      everything else, each row with its reason

Scope (DECISIONS #19): Kargin Haghordum, Kargin Multer, Kargin Kaset. Not Kargin
Sketch Show, not Kargin Serial / Azizyanner, not the "No Comment" stage show. Anything that can't be placed is kept
with series=unclear for the human triage rather than dropped.

Usage (~2 s):
  uv run python scripts/non_essential/triage_candidates.py
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCOUT = ROOT / "data" / "channel_scout" / "videos.csv"
CAND = ROOT / "data" / "candidates"
COMP = ROOT / "data" / "compilations"

(ROOT / "logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(ROOT / "logs" / "triage_candidates.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("triage_candidates")

STANDALONE_MAX = 480   # above this, 90 s of audio can't show a second sketch: pool it
SHORT_MIN = 60         # below this it's a short or a clip of one sketch

OUT_OF_SCOPE = [
    ("sketch_show", re.compile(r"sketch\s*show", re.I)),
    ("serial", re.compile(r"serial|сериал|սերիալ|aziz|ազիզ", re.I)),
    ("ad_or_politics", re.compile(r"halal|govazd|գովազդ|anons|trailer|ընտր|քաղաքապետ|#նոր_ուժ", re.I)),
    # KarginTV's 2012-2013 "No Comment" stage show (12 uploads): out of scope (owner, Q21, 2026-11-03)
    ("no_comment_stage_show", re.compile(r"no\s*comment", re.I)),
]
SERIES = [
    ("no_comment", re.compile(r"no\s*comment", re.I)),
    ("multer", re.compile(r"multer|մուլտ", re.I)),
    ("kaset", re.compile(r"kaset|կասետ|кассет", re.I)),
    ("haghordum", re.compile(
        r"haghordum|haxordum|hakhordum|xaxordum|хахордум|հաղորդում|hayko\W{0,5}(?:u|ev|and|&|-)?\W{0,3}mko"
        r"|mko\W{0,5}(?:u|ev|and|&|-)?\W{0,3}hayko|haykomko|հայկո\W{0,5}(?:ու|և)?\W{0,3}մկո", re.I)),
]
# Other Armenian comedy shows that fan channels hashtag #Կարգին for reach (season/episode
# numbering, show names). Applied ONLY to titles with no Kargin series marker, so a title
# that says "Kargin Haghordum" is never dropped by it. Measured 2026-11-03: removes 266 of
# 927 unmarked candidates; the other 661 are left to the audio match (DECISIONS #19).
OTHER_SHOW = re.compile(
    r"սերիա|եթերաշրջան|серия|сезон|season|episode|bolola|vitamin|womens\s*club|ponch|ziroyan"
    r"|eleni|էլենի|banakum|բանակում|bazar\s*blot|super\s*saqo|azat\s*ev\s*ankax", re.I)
COMPILATION_TITLE = re.compile(
    r"best of|the best|top\s*\d|топ|լավագույն|подборка|сборник|\bmix\b|compilation|full|ամբողջական"
    r"|թողարկում|episode|выпуск|bocer|բոցեր|part\s*\d", re.I)


def series_of(title: str) -> str:
    for name, rx in SERIES:
        if rx.search(title):
            return name
    return "unclear"


def archive_compilations() -> list[str]:
    """Archive videos the visual pass described as compilations (DECISIONS #19, Q14)."""
    out = []
    for p in sorted((ROOT / "data" / "visual_annotations").glob("*.json")):
        text = p.read_text(encoding="utf-8")
        low = text.lower()
        if any(w in low for w in ("compilation", "multiple sketches", "several sketches", "separate sketches")):
            out.append(json.loads(text)["video_id"])   # ids are case-sensitive: parse the original
    return out


def main() -> None:
    t0 = time.time()
    v = pd.read_csv(SCOUT, dtype={"video_id": str})
    log.info(f"scout rows: {len(v)} from {v.channel_id.nunique()} channels")
    v = v[v["privacy"].fillna("") != "unavailable"].copy()
    v["duration_sec"] = v["duration_sec"].fillna(0)
    v["series"] = v["title"].fillna("").map(series_of)
    v["source"] = v["channel_title"].eq("KarginTV").map({True: "kargintv", False: "fan"})

    cand, pool, skip = [], [], []
    for _, r in v.iterrows():
        title, dur = str(r.title or ""), float(r.duration_sec)
        rec = r.to_dict()
        if r.in_archive:
            skip.append({**rec, "reason": "already in the archive"})
            continue
        # Out-of-scope shows are judged on the title WITHOUT hashtags: fan channels spam
        # #karginserial on unrelated uploads, which dropped 19 Kargin videos and 2 compilations
        # (methodology review F7). The other-show filter below keeps hashtags: #bolola is real
        # evidence of another show.
        plain = re.sub(r"#\S+", " ", title)
        out = next((name for name, rx in OUT_OF_SCOPE if rx.search(plain)), None)
        if out:
            skip.append({**rec, "reason": f"out of scope: {out}"})
            continue
        if r.source == "kargintv" and r.series == "unclear":
            # KarginTV's non-sketch uploads: politics, theatre, promos. Kept visible in skipped.
            skip.append({**rec, "reason": "KarginTV upload with no Kargin series in the title"})
            continue
        if r.series == "unclear" and OTHER_SHOW.search(title):
            skip.append({**rec, "reason": "other show by title (no Kargin marker)"})
            continue
        if dur < SHORT_MIN:
            skip.append({**rec, "reason": "short (<60 s): a clip of one sketch"})
            continue
        if dur > STANDALONE_MAX or COMPILATION_TITLE.search(title):
            why = "longer than 480 s" if dur > STANDALONE_MAX else "titled like a compilation"
            pool.append({**rec, "pool_reason": why})
            continue
        cand.append(rec)

    meta = pd.read_csv(ROOT / "data" / "youtube_metadata.csv", dtype={"video_id": str}).set_index("video_id")
    for vid in archive_compilations():
        pool.append({"video_id": vid, "channel_title": "KarginTV", "title": meta.at[vid, "title"],
                     "duration_sec": meta.at[vid, "duration_sec"], "source": "archive",
                     "series": "haghordum", "in_archive": True,
                     "url": f"https://www.youtube.com/watch?v={vid}",
                     "pool_reason": "archive video the visual pass called a compilation"})

    CAND.mkdir(parents=True, exist_ok=True)
    COMP.mkdir(parents=True, exist_ok=True)
    cols = ["video_id", "source", "series", "channel_id", "channel_title", "title", "duration_sec",
            "upload_date", "view_count", "url"]
    # KarginTV first: if YouTube's bot check stops the screening download partway,
    # the official uploads (the most valuable rows) are already done.
    cdf = pd.DataFrame(cand)[cols]
    cdf = cdf.assign(_fan=cdf["source"].ne("kargintv")).sort_values(["_fan", "channel_title", "video_id"])
    cdf.drop(columns="_fan").to_csv(CAND / "candidates.csv", index=False, encoding="utf-8")
    pd.DataFrame(pool)[cols + ["pool_reason"]].to_csv(COMP / "pool.csv", index=False, encoding="utf-8")
    pd.DataFrame(skip)[cols + ["reason"]].to_csv(CAND / "skipped.csv", index=False, encoding="utf-8")

    log.info(f"candidates: {len(cand)}  by source {dict(Counter(c['source'] for c in cand))}  "
             f"by series {dict(Counter(c['series'] for c in cand))}")
    log.info(f"pool: {len(pool)}  by reason {dict(Counter(p['pool_reason'] for p in pool))}  "
             f"minutes {sum(float(p['duration_sec'] or 0) for p in pool) / 60:.0f}")
    log.info(f"skipped: {len(skip)}  by reason {dict(Counter(s['reason'] for s in skip))}")
    log.info(f"done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
