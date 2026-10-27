"""
Map the YouTube channels that upload Kargin sketches, to find the ones missing
from the archive (all 702 archive sketches come from the one KarginTV channel).

Seeds, both in data/channel_scout/:
  seeds.json            hand-entered videos and channels (chat links, known channels)
  pw_search_hits.json   videos and channel results scraped from YouTube search with
                        Playwright (optional; channel results only if the name or
                        blurb says kargin/կարգին)

Every channel a seed video belongs to becomes a channel too. For each channel the
script lists its uploads (title + description), keeps the ones with a Kargin
signal (or ALL of them for a dedicated channel: at least half the uploads have a
signal, or the channel's own name has one), and fetches duration/views for what
it keeps. Metadata only, nothing is downloaded.

"kargin" alone is NOT a signal: Kargın is a common Turkish/Russian surname and the
channel search returns dozens of such people. Nor is a lone "Hayko" (a famous singer)
or "Mko": only the pair counts. See KARGIN_SIGNAL.

Writes to data/channel_scout/:
  channels.json           channels with at least one Kargin-signal upload, or a hand seed
  channels_rejected.json  channels with none, with their counts (nothing dropped silently)
  videos.json             kept uploads plus seed info (artifact of record)
  videos.csv              the same rows without descriptions, for a spreadsheet

Quota: ~1 unit per 50 uploads listed + 1 per 50 kept, of the free 10,000/day.
A channel above --max-uploads is cut at that many newest uploads, with a WARNING
and `uploads_truncated: true`.

Usage (~2-8 min with search hits, mostly the big channels; ~1 min hand seeds only):
  uv run python scripts/non_essential/scout_channels.py
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "channel_scout"
API = "https://www.googleapis.com/youtube/v3"

(ROOT / "logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(ROOT / "logs" / "scout_channels.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("scout_channels")

# Hayko and Mko only as a pair, in either order: "Hayko Mko", "(Hayko & Mko)", "#haykomko",
# "Հայկոն ու Մկոն". The first run counted them alone and kept 75 songs by the singer
# HT Hayko and a channel's birthday wishes to a Hayko (2.5% of matching rows).
_PAIR = r"{a}\w{{0,3}}\W{{0,5}}(?:(?:{j})\W{{1,3}})?{b}"
KARGIN_SIGNAL = re.compile(
    r"կարգին|haxordum|haghordum|hakhordum|xaxordum|хахордум|kaset|կասետ"
    r"|kargin\s*(?:show|serial|sketch|shorts|tv|club|humor|tube)|"
    + "|".join(_PAIR.format(a=a, b=b, j=j) for a, b, j in [
        ("hayko", "mko", "u|ev|and|i"), ("mko", "hayko", "u|ev|and|i"),
        ("հայկո", "մկո", "ու|և|եւ"), ("մկո", "հայկո", "ու|և|եւ"),
    ]),
    re.IGNORECASE,
)
ANY_KARGIN = re.compile(r"kargin|կարգին|каргин", re.IGNORECASE)
DEDICATED_SHARE = 0.5
ISO_DUR = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


# Copied from fetch_youtube_metadata_api.py: importing it would run its module-level
# logging.basicConfig and send this script's log lines to that script's file.
def parse_iso_duration(s: str | None) -> int | None:
    m = ISO_DUR.fullmatch(s or "")
    if not m:
        return None
    h, mn, sc = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mn * 60 + sc


def yyyymmdd(iso: str | None) -> str | None:
    return iso[:10].replace("-", "") if iso else None


def get(endpoint: str, key: str, **params) -> dict:
    r = requests.get(f"{API}/{endpoint}", params={**params, "key": key}, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"{endpoint} {r.status_code}: {r.text[:300]}")
    return r.json()


def fetch_videos(key: str, ids: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for i in range(0, len(ids), 50):
        data = get("videos", key, part="snippet,contentDetails,statistics,status", id=",".join(ids[i:i + 50]))
        out.update({it["id"]: it for it in data.get("items", [])})
    return out


def fetch_channels(key: str, ids: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for i in range(0, len(ids), 50):
        data = get("channels", key, part="snippet,statistics,contentDetails", id=",".join(ids[i:i + 50]))
        out.update({it["id"]: it for it in data.get("items", [])})
    return out


def resolve_handle(key: str, handle: str) -> str | None:
    items = get("channels", key, part="id", forHandle=handle).get("items", [])
    return items[0]["id"] if items else None


def list_uploads(key: str, playlist: str, cap: int) -> tuple[list[dict], bool]:
    """Uploads (id, title, description), newest first. True if cut at cap."""
    ups: list[dict] = []
    token = None
    while True:
        params = {"part": "snippet", "playlistId": playlist, "maxResults": 50}
        if token:
            params["pageToken"] = token
        data = get("playlistItems", key, **params)
        for it in data.get("items", []):
            sn = it["snippet"]
            ups.append({"id": sn["resourceId"]["videoId"], "title": sn.get("title") or "",
                        "description": sn.get("description") or ""})
        token = data.get("nextPageToken")
        if not token:
            return ups, False
        if len(ups) >= cap:
            return ups[:cap], True


def video_row(item: dict, archive_ids: set[str], seed: dict | None) -> dict:
    sn, cd, st = item.get("snippet", {}), item.get("contentDetails", {}), item.get("statistics", {})
    title = sn.get("title") or ""
    return {
        "video_id": item["id"],
        "channel_id": sn.get("channelId"),
        "channel_title": sn.get("channelTitle"),
        "title": title,
        "duration_sec": parse_iso_duration(cd.get("duration")),
        "upload_date": yyyymmdd(sn.get("publishedAt")),
        "view_count": int(st["viewCount"]) if "viewCount" in st else None,
        "like_count": int(st["likeCount"]) if "likeCount" in st else None,
        "comment_count": int(st["commentCount"]) if "commentCount" in st else None,
        "privacy": item.get("status", {}).get("privacyStatus"),
        "in_archive": item["id"] in archive_ids,
        "kargin_signal": bool(KARGIN_SIGNAL.search(f"{title}\n{sn.get('description') or ''}")),
        "title_mentions_kargin": bool(ANY_KARGIN.search(title)),
        "is_seed": seed is not None,
        "seed_source": (seed or {}).get("source"),
        "seed_t": (seed or {}).get("t"),
        "seed_note": (seed or {}).get("note"),
        "url": f"https://www.youtube.com/watch?v={item['id']}",
        "description": sn.get("description"),
    }


def load_seeds() -> tuple[dict[str, dict], list[dict]]:
    """Hand seeds first, so a chat link keeps its 'chat' source when search found it too."""
    hand = json.loads((OUT / "seeds.json").read_text(encoding="utf-8"))
    videos = {v["video_id"]: v for v in hand["videos"]}
    channels = list(hand["channels"])
    hits_file = OUT / "pw_search_hits.json"
    if hits_file.exists():
        hits = json.loads(hits_file.read_text(encoding="utf-8"))
        for vid, h in hits["videos"].items():
            videos.setdefault(vid, {"video_id": vid, "source": f"pw-search: {h['q']}"})
        named = 0
        for href, h in hits["channels"].items():
            if not ANY_KARGIN.search(f"{href} {h['text']}"):
                continue
            named += 1
            ref = {"channel_id": href.split("/channel/")[1]} if "/channel/" in href else {"handle": href.lstrip("/")}
            channels.append({**ref, "source": f"pw-channel-search: {h['q']}"})
        log.info(f"search hits: {len(hits['videos'])} videos, {named} of {len(hits['channels'])} channel results named kargin")
    return videos, channels


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-uploads", type=int, default=3000, help="per-channel cap on listed uploads")
    args = ap.parse_args()
    t0 = time.time()

    load_dotenv(ROOT / ".env")
    key = os.environ.get("YOUTUBE_DATA_API_KEY")
    if not key:
        raise RuntimeError("YOUTUBE_DATA_API_KEY missing from .env")

    seed_videos, seed_channels = load_seeds()
    archive_ids = set(pd.read_csv(ROOT / "kargin_eng.csv", dtype=str)["video_id"].dropna())

    seed_items = fetch_videos(key, list(seed_videos))
    gone = sorted(set(seed_videos) - set(seed_items))
    for vid in gone:
        log.warning(f"seed video {vid} ({seed_videos[vid]['source']}) not returned by the API (private, deleted or bad id)")

    found_via: dict[str, list[str]] = {}
    hand_channels: set[str] = set()
    for it in seed_items.values():
        found_via.setdefault(it["snippet"]["channelId"], []).append(f"{seed_videos[it['id']]['source']} -> {it['id']}")
        if seed_videos[it["id"]]["source"] == "chat":
            hand_channels.add(it["snippet"]["channelId"])
    unresolved = []
    for ch in seed_channels:
        cid = ch.get("channel_id") or resolve_handle(key, ch["handle"])
        if cid is None:
            unresolved.append(ch["handle"])
            continue
        found_via.setdefault(cid, []).append(f"{ch['source']}: {ch.get('handle', cid)}")
        if not ch["source"].startswith("pw-"):
            hand_channels.add(cid)
    if unresolved:
        log.warning(f"{len(unresolved)} handles did not resolve: {unresolved}")

    channels = fetch_channels(key, list(found_via))
    missing = set(found_via) - set(channels)
    if missing:
        raise RuntimeError(f"channels.list returned nothing for {sorted(missing)}")
    log.info(f"{len(seed_items)} seed videos, {len(channels)} channels to scan")

    rows: list[dict] = []
    kept_records: list[dict] = []
    rejected: list[dict] = []
    for n, (cid, ch) in enumerate(channels.items(), 1):
        title = ch["snippet"]["title"]
        playlist = ch.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
        try:
            uploads, truncated = list_uploads(key, playlist, args.max_uploads) if playlist else ([], False)
        except RuntimeError as e:
            # e.g. auto-generated "- Topic" channels whose uploads playlist 404s
            log.error(f"{title} ({cid}): cannot list uploads: {e}")
            rejected.append({"channel_id": cid, "title": title, "error": str(e)[:200], "found_via": found_via[cid]})
            continue
        if truncated:
            log.warning(f"{title}: cut at {args.max_uploads} newest uploads")
        signal = [u for u in uploads if KARGIN_SIGNAL.search(f"{u['title']}\n{u['description']}")]
        # A channel called "ԿԱՐԳԻՆ HUB" whose shorts are titled only with emoji is still a
        # Kargin channel: the second run rejected a dozen like that on upload titles alone.
        named = bool(KARGIN_SIGNAL.search(title))
        dedicated = bool(uploads) and (named or len(signal) / len(uploads) >= DEDICATED_SHARE)
        own_seeds = [vid for vid, it in seed_items.items() if it["snippet"]["channelId"] == cid]
        st = ch.get("statistics", {})
        record = {
            "channel_id": cid,
            "title": title,
            "handle": ch["snippet"].get("customUrl"),
            "url": f"https://www.youtube.com/channel/{cid}",
            "created": yyyymmdd(ch["snippet"].get("publishedAt")),
            "country": ch["snippet"].get("country"),
            "subscribers": int(st["subscriberCount"]) if "subscriberCount" in st else None,
            "video_count_reported": int(st.get("videoCount", 0)),
            "uploads_listed": len(uploads),
            "uploads_truncated": truncated,
            "uploads_with_signal": len(signal),
            "kept": ("all (name)" if named else "all (share)") if dedicated else "signal-only",
            "found_via": found_via[cid],
        }
        if cid not in hand_channels and not (signal or (named and uploads)):
            rejected.append(record)
        else:
            keep = [u["id"] for u in (uploads if dedicated else signal)]
            keep += [vid for vid in own_seeds if vid not in set(keep)]
            items = fetch_videos(key, keep)
            ch_rows = [video_row(it, archive_ids, seed_videos.get(vid)) for vid, it in items.items()]
            rows += ch_rows
            record |= {
                "videos_kept": len(ch_rows),
                "in_archive": sum(r["in_archive"] for r in ch_rows),
                "seed_videos": sum(r["is_seed"] for r in ch_rows),
                "total_views_kept": sum(r["view_count"] or 0 for r in ch_rows),
            }
            kept_records.append(record)
        el = time.time() - t0
        log.info(f"[{n}/{len(channels)}] {title}: {len(uploads)} uploads, {len(signal)} with signal, "
                 f"{'kept ' + record['kept'] if record in kept_records else 'rejected'}  "
                 f"({el:.0f}s elapsed, ~{el / n * (len(channels) - n):.0f}s left)")

    for vid in gone:
        s = seed_videos[vid]
        rows.append({"video_id": vid, "privacy": "unavailable", "is_seed": True, "in_archive": vid in archive_ids,
                     "seed_source": s.get("source"), "seed_t": s.get("t"), "seed_note": s.get("note"),
                     "url": f"https://www.youtube.com/watch?v={vid}"})

    kept_records.sort(key=lambda c: -c["uploads_with_signal"])
    rejected.sort(key=lambda c: c["title"])
    (OUT / "channels.json").write_text(json.dumps(kept_records, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "channels_rejected.json").write_text(json.dumps(rejected, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "videos.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(rows).drop(columns=["description"]).to_csv(OUT / "videos.csv", index=False, encoding="utf-8")
    log.info(f"{len(kept_records)} channels kept, {len(rejected)} rejected, {len(rows)} videos -> {OUT}  "
             f"({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
