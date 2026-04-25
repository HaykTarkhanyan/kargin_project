"""Fetch YouTube metadata via the YouTube Data API v3.

Faster and more reliable than the yt-dlp version (no rate limits, no cookies),
but provides less data: caption-language detail would cost 50 quota units per
video (3.5x daily quota for 695 videos), and the API doesn't expose chapters.
For our project both are acceptable losses — see PLAN.md / LEARNINGS.md.

Reads YOUTUBE_DATA_API_KEY from .env (or the environment).
Writes the same schema as fetch_youtube_metadata.py to data/youtube_metadata.csv,
plus a `source` column ("api" here vs "yt-dlp" from the other script) and a
cheap boolean `caption_available` from contentDetails.caption.

Resume-safe: skips video_ids already present with empty fetch_error. Migrates
the older yt-dlp-only schema by adding the new columns and tagging existing
rows with `source = "yt-dlp"`.

Usage:
    uv run python scripts/fetch_youtube_metadata_api.py
    uv run python scripts/fetch_youtube_metadata_api.py --limit 50
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd
import requests
from dotenv import load_dotenv


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "fetch_youtube_metadata_api.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)


API_URL = "https://www.googleapis.com/youtube/v3/videos"
BATCH_SIZE = 50  # API max per call


SCHEMA: list[str] = [
    "video_id",
    "canonical_url",
    "original_url",
    "title",
    "uploader",
    "channel_id",
    "duration_sec",
    "upload_date",
    "view_count",
    "like_count",
    "dislike_count",
    "comment_count",
    "availability",
    "yt_declared_language",
    "categories",
    "tags",
    "subs_manual_langs",         # only set by yt-dlp script
    "auto_caption_source_lang",  # only set by yt-dlp script
    "has_auto_captions",         # only set by yt-dlp script
    "caption_available",         # cheap bool from API contentDetails.caption
    "has_chapters",              # only set by yt-dlp script
    "chapters_count",            # only set by yt-dlp script
    "chapters_json",             # only set by yt-dlp script
    "description",
    "source",                    # "api" | "yt-dlp"
    "fetched_at",
    "fetch_error",
]


_ISO_DUR = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def parse_iso_duration(s: str | None) -> int | None:
    """ISO 8601 duration like 'PT2M30S' -> seconds."""
    if not s:
        return None
    m = _ISO_DUR.fullmatch(s)
    if not m:
        return None
    h, mn, sc = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mn * 60 + sc


def parse_iso_date_to_yyyymmdd(s: str | None) -> str | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.strftime("%Y%m%d")
    except Exception:
        return None


def extract_video_id(url: str) -> str | None:
    if not isinstance(url, str) or not url.strip():
        return None
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if host in ("youtu.be", "www.youtu.be"):
        vid = parsed.path.lstrip("/")
        return vid or None
    if host in ("youtube.com", "www.youtube.com", "m.youtube.com"):
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [None])[0]
        if parsed.path.startswith(("/embed/", "/v/", "/shorts/")):
            parts = parsed.path.split("/")
            if len(parts) >= 3 and parts[2]:
                return parts[2]
    return None


def fetch_batch(api_key: str, ids: list[str]) -> dict[str, dict]:
    """Hit the API for up to 50 video IDs. Returns {video_id: raw_item}.

    Raises RuntimeError on quota exceeded or other API errors. Caller decides
    whether to mark each video as failed or stop the run.
    """
    params = {
        "part": "snippet,contentDetails,statistics,status",
        "id": ",".join(ids),
        "key": api_key,
        "maxResults": str(BATCH_SIZE),
    }
    r = requests.get(API_URL, params=params, timeout=30)
    if r.status_code == 403:
        # quota / disabled api / blocked key
        raise RuntimeError(f"403 from API (quota or auth): {r.text[:300]}")
    r.raise_for_status()
    data = r.json()
    return {it["id"]: it for it in data.get("items", [])}


def item_to_row(item: dict, original_url: str) -> dict:
    vid = item["id"]
    snippet = item.get("snippet", {}) or {}
    content = item.get("contentDetails", {}) or {}
    stats = item.get("statistics", {}) or {}
    status = item.get("status", {}) or {}

    def _to_int(v):
        return int(v) if v is not None and str(v).strip() != "" else None

    return {
        "video_id": vid,
        "canonical_url": f"https://www.youtube.com/watch?v={vid}",
        "original_url": original_url,
        "title": snippet.get("title"),
        "uploader": snippet.get("channelTitle"),
        "channel_id": snippet.get("channelId"),
        "duration_sec": parse_iso_duration(content.get("duration")),
        "upload_date": parse_iso_date_to_yyyymmdd(snippet.get("publishedAt")),
        "view_count": _to_int(stats.get("viewCount")),
        "like_count": _to_int(stats.get("likeCount")),
        "dislike_count": None,  # YouTube hid public dislikes in 2021
        "comment_count": _to_int(stats.get("commentCount")),
        "availability": status.get("privacyStatus"),
        "yt_declared_language": snippet.get("defaultLanguage")
        or snippet.get("defaultAudioLanguage"),
        "categories": json.dumps(
            [snippet["categoryId"]] if snippet.get("categoryId") else [],
            ensure_ascii=False,
        ),
        "tags": json.dumps(snippet.get("tags") or [], ensure_ascii=False)[:5000],
        "subs_manual_langs": "",
        "auto_caption_source_lang": "",
        "has_auto_captions": "",
        "caption_available": str(content.get("caption", "")).lower() == "true",
        "has_chapters": "",
        "chapters_count": "",
        "chapters_json": "",
        "description": (snippet.get("description") or "")[:1000],
        "source": "api",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fetch_error": "",
    }


def error_row(video_id: str, original_url: str, error: str) -> dict:
    row = {k: None for k in SCHEMA}
    row.update(
        {
            "video_id": video_id,
            "canonical_url": f"https://www.youtube.com/watch?v={video_id}",
            "original_url": original_url,
            "categories": "[]",
            "tags": "[]",
            "subs_manual_langs": "",
            "auto_caption_source_lang": "",
            "has_auto_captions": "",
            "caption_available": "",
            "has_chapters": "",
            "chapters_count": "",
            "chapters_json": "",
            "description": "",
            "source": "api",
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "fetch_error": error,
        }
    )
    return row


def load_resume(output_csv: Path) -> tuple[list[dict], set[str]]:
    """Load existing CSV, migrate schema if needed, return (rows, succeeded_ids).

    Migration: prior rows from the yt-dlp script don't have `source` or
    `caption_available` columns. Fill `source = "yt-dlp"` for them, leave
    `caption_available` blank.
    """
    if not output_csv.exists():
        return [], set()
    prior = pd.read_csv(output_csv)
    migrated = False
    if "source" not in prior.columns:
        prior["source"] = "yt-dlp"
        migrated = True
    if "caption_available" not in prior.columns:
        prior["caption_available"] = ""
        migrated = True
    for col in SCHEMA:
        if col not in prior.columns:
            prior[col] = None
    prior = prior[SCHEMA]
    if migrated:
        logging.info("migrating prior CSV: tagged existing rows with source=yt-dlp")

    rows = prior.to_dict(orient="records")
    succeeded: set[str] = set()
    for r in rows:
        vid = str(r.get("video_id") or "")
        if not vid:
            continue
        err = r.get("fetch_error")
        has_error = not pd.isna(err) and str(err) != ""
        if not has_error:
            succeeded.add(vid)
    logging.info(f"resume: {len(rows)} prior rows, {len(succeeded)} succeeded")
    return rows, succeeded


def flush(rows_by_vid: dict[str, dict], output_csv: Path) -> None:
    df_out = pd.DataFrame(list(rows_by_vid.values()), columns=SCHEMA)
    df_out.to_csv(output_csv, index=False, encoding="utf-8")
    logging.info(f"  flushed {len(df_out)} rows -> {output_csv}")


def main(input_csv: Path, output_csv: Path, limit: int | None) -> int:
    load_dotenv()
    api_key = os.getenv("YOUTUBE_DATA_API_KEY")
    if not api_key:
        logging.error(
            "YOUTUBE_DATA_API_KEY not set. Add it to .env at the project root."
        )
        return 2

    if not input_csv.exists():
        logging.error(f"input not found: {input_csv}")
        return 2

    df = pd.read_csv(input_csv)
    if "links" not in df.columns:
        logging.error(
            f"{input_csv} has no 'links' column. Columns: {list(df.columns)}"
        )
        return 2

    raw = df["links"].dropna().tolist()
    logging.info(f"loaded {len(raw)} non-null URLs from {input_csv}")

    seen: dict[str, str] = {}
    skipped_no_id: list[str] = []
    for url in raw:
        vid = extract_video_id(url)
        if vid is None:
            skipped_no_id.append(url)
            continue
        seen.setdefault(vid, url)
    logging.info(
        f"unique video_ids: {len(seen)}, skipped (unparsable URL): {len(skipped_no_id)}"
    )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    existing_rows, succeeded = load_resume(output_csv)
    rows_by_vid: dict[str, dict] = {
        str(r.get("video_id") or ""): r
        for r in existing_rows
        if str(r.get("video_id") or "")
    }

    todo = [(vid, url) for vid, url in seen.items() if vid not in succeeded]
    if limit is not None:
        todo = todo[:limit]

    logging.info(
        f"will fetch {len(todo)} videos in {(len(todo) + BATCH_SIZE - 1) // BATCH_SIZE} "
        f"batches of up to {BATCH_SIZE}"
    )

    if not todo:
        flush(rows_by_vid, output_csv)
        logging.info("nothing to fetch")
        return 0

    success = 0
    failed = 0

    for batch_start in range(0, len(todo), BATCH_SIZE):
        batch = todo[batch_start : batch_start + BATCH_SIZE]
        ids = [vid for vid, _ in batch]
        url_by_id = {vid: url for vid, url in batch}

        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (len(todo) + BATCH_SIZE - 1) // BATCH_SIZE
        logging.info(f"[batch {batch_num}/{total_batches}] requesting {len(ids)} ids")

        try:
            items = fetch_batch(api_key, ids)
        except Exception as e:
            err = f"batch fetch failed: {str(e).splitlines()[0][:300]}"
            logging.error(err)
            for vid in ids:
                rows_by_vid[vid] = error_row(vid, url_by_id[vid], err)
                failed += 1
            flush(rows_by_vid, output_csv)
            # Quota / auth failures will affect every subsequent batch too;
            # bail out loudly so the user notices.
            if "403" in err or "quota" in err.lower():
                logging.error("API auth/quota error — stopping")
                return 1
            continue

        for vid in ids:
            if vid in items:
                row = item_to_row(items[vid], url_by_id[vid])
                rows_by_vid[vid] = row
                success += 1
                title = (row.get("title") or "")[:60]
                logging.info(f"  {vid} ok ({row.get('duration_sec')}s) {title}")
            else:
                rows_by_vid[vid] = error_row(
                    vid,
                    url_by_id[vid],
                    "video not in API response (deleted/private/region-locked)",
                )
                failed += 1
                logging.error(f"  {vid} not in API response")

        flush(rows_by_vid, output_csv)

    logging.info(
        f"done. this run: {success} ok, {failed} failed. "
        f"total rows in {output_csv}: {len(rows_by_vid)}"
    )
    if skipped_no_id:
        logging.warning(
            f"reminder: {len(skipped_no_id)} URLs had no parsable video_id and were skipped"
        )
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", default="kargin_eng.csv", type=Path)
    p.add_argument("--output", default=Path("data/youtube_metadata.csv"), type=Path)
    p.add_argument("--limit", type=int, default=None, help="for smoke testing")
    args = p.parse_args()
    sys.exit(main(args.input, args.output, args.limit))
