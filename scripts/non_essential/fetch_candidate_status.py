"""
Fetch the playability facts the copy choice needs (plan step A5, Q8 hard requirements):
is each candidate public, embeddable, unblocked in Armenia and Germany, not
age-restricted, and HD? Our site plays videos in a YouTube iframe, so a video that
fails any of these plays nothing on our page.

Reads data/candidates/candidates.csv and data/compilations/pool.csv; writes
data/candidates/status.csv (one row per video). YouTube Data API v3, part
status+contentDetails: 1 quota unit per 50 videos (~45 units for ~2,250 videos, of the
free 10,000/day). A video the API no longer returns is written as `gone`, not dropped.

Usage (~30 s):
  uv run python scripts/non_essential/fetch_candidate_status.py
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "candidates" / "status.csv"
COUNTRIES = ("AM", "DE")   # where the owner and most of the audience are

log = logging.getLogger("fetch_candidate_status")


def playable_in(region: dict, country: str) -> bool:
    """regionRestriction has either an allow-list or a block-list (or neither)."""
    if "allowed" in region:
        return country in region["allowed"]
    return country not in region.get("blocked", [])


def row_for(vid: str, item: dict | None) -> dict:
    if item is None:
        return {"video_id": vid, "status": "gone"}
    st, cd = item.get("status", {}), item.get("contentDetails", {})
    region = cd.get("regionRestriction", {})
    age = cd.get("contentRating", {}).get("ytRating") == "ytAgeRestricted"
    row = {
        "video_id": vid,
        "privacy": st.get("privacyStatus"),
        "embeddable": bool(st.get("embeddable")),
        "age_restricted": age,
        "definition": cd.get("definition"),
        "licensed_content": cd.get("licensedContent"),
        "region_restriction": json.dumps(region) if region else "",
    }
    for c in COUNTRIES:
        row[f"playable_{c}"] = playable_in(region, c)
    ok = (row["privacy"] == "public" and row["embeddable"] and not age
          and all(row[f"playable_{c}"] for c in COUNTRIES))
    row["status"] = "ok" if ok else "fails_hard_requirements"
    return row


def main() -> None:
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(),
                                  logging.FileHandler(ROOT / "logs" / "fetch_candidate_status.log", encoding="utf-8")])
    t0 = time.time()
    load_dotenv(ROOT / ".env")
    key = os.environ.get("YOUTUBE_DATA_API_KEY")
    if not key:
        raise RuntimeError("YOUTUBE_DATA_API_KEY missing from .env")
    ids: list[str] = []
    for src in (ROOT / "data" / "candidates" / "candidates.csv", ROOT / "data" / "compilations" / "pool.csv"):
        ids += pd.read_csv(src, dtype={"video_id": str})["video_id"].tolist()
    ids = list(dict.fromkeys(ids))
    items: dict[str, dict] = {}
    for i in range(0, len(ids), 50):
        r = requests.get("https://www.googleapis.com/youtube/v3/videos", timeout=30, params={
            "part": "status,contentDetails", "id": ",".join(ids[i:i + 50]), "key": key})
        if r.status_code != 200:
            raise RuntimeError(f"videos.list {r.status_code}: {r.text[:300]}")
        items.update({it["id"]: it for it in r.json().get("items", [])})
    df = pd.DataFrame([row_for(v, items.get(v)) for v in ids])
    df["fetched_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    df.to_csv(OUT, index=False, encoding="utf-8")
    log.info(f"{len(df)} videos -> {OUT}: {df.status.value_counts().to_dict()}")
    bad = df[df.status == "fails_hard_requirements"]
    if len(bad):
        log.info("why they fail: " + str({
            "not public": int((bad.privacy != "public").sum()),
            "not embeddable": int((~bad.embeddable.astype(bool)).sum()),
            "age-restricted": int(bad.age_restricted.astype(bool).sum()),
            **{f"blocked in {c}": int((~bad[f"playable_{c}"].astype(bool)).sum()) for c in COUNTRIES}}))
    log.info(f"HD: {int((df.definition == 'hd').sum())}, SD: {int((df.definition == 'sd').sum())}; "
             f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
