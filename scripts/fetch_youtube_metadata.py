"""Fetch YouTube metadata for every URL in kargin_eng.csv via yt-dlp.

Output: one row per unique YouTube video_id, with metadata + a fetch_error column
so failures are visible (deleted/private/region-locked videos do not abort the run).

Idempotent: re-running skips video_ids already present with fetch_error == "".
Parallel: uses a ThreadPoolExecutor; yt-dlp metadata calls are network-bound so
threads (not processes) are the right model. Default 8 workers — bump higher only
if you don't see YouTube throttling kicking in.

Fails loudly on invalid input (missing columns, missing input file). Per-video
fetch failures are recorded as rows with fetch_error set; they don't abort the run.

Usage:
    uv run python scripts/fetch_youtube_metadata.py
    uv run python scripts/fetch_youtube_metadata.py --limit 6 --workers 4
    uv run python scripts/fetch_youtube_metadata.py --output data/x.csv
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd
import yt_dlp


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "fetch_youtube_metadata.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)


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
    "dislike_count",  # ~always None since YouTube hid dislikes in 2021
    "comment_count",
    "availability",
    "yt_declared_language",  # YouTube's guess, unreliable for Armenian
    "categories",
    "tags",
    "subs_manual_langs",         # comma-sep list of manually-uploaded caption langs
    "auto_caption_source_lang",  # the lang YouTube actually auto-transcribed in (e.g. "ru"); empty if no auto-captions
    "has_auto_captions",         # bool: did YouTube auto-process this video at all
    "has_chapters",
    "chapters_count",
    "chapters_json",
    "description",
    "fetched_at",
    "fetch_error",
]


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


_COOKIES_FROM_BROWSER: tuple | None = None  # set by main()


def fetch_metadata(video_id: str, original_url: str) -> dict:
    canonical_url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
    }
    if _COOKIES_FROM_BROWSER is not None:
        # yt-dlp expects a tuple like ("firefox",) or ("chrome", "Default", None, None).
        ydl_opts["cookiesfrombrowser"] = _COOKIES_FROM_BROWSER
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(canonical_url, download=False)

    subs_manual_keys = sorted((info.get("subtitles") or {}).keys())
    auto_caption_keys = list((info.get("automatic_captions") or {}).keys())
    # YouTube's automatic_captions dict has keys like "en", "ru", "fr-FR" plus
    # one "<lang>-orig" entry marking the SOURCE language (everything else is
    # YouTube auto-translating from that source). The "-orig" entry is what we
    # actually care about; the rest is noise.
    orig_keys = [k for k in auto_caption_keys if k.endswith("-orig")]
    auto_caption_source_lang = orig_keys[0].removesuffix("-orig") if orig_keys else ""
    has_auto_captions = bool(auto_caption_keys)

    chapters = info.get("chapters") or []
    tags = info.get("tags") or []
    categories = info.get("categories") or []
    description = info.get("description") or ""

    return {
        "video_id": video_id,
        "canonical_url": canonical_url,
        "original_url": original_url,
        "title": info.get("title"),
        "uploader": info.get("uploader"),
        "channel_id": info.get("channel_id"),
        "duration_sec": info.get("duration"),
        "upload_date": info.get("upload_date"),  # YYYYMMDD string
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "dislike_count": info.get("dislike_count"),
        "comment_count": info.get("comment_count"),
        "availability": info.get("availability"),
        "yt_declared_language": info.get("language"),
        "categories": json.dumps(categories, ensure_ascii=False),
        "tags": json.dumps(tags, ensure_ascii=False)[:5000],
        "subs_manual_langs": ",".join(subs_manual_keys),
        "auto_caption_source_lang": auto_caption_source_lang,
        "has_auto_captions": has_auto_captions,
        "has_chapters": bool(chapters),
        "chapters_count": len(chapters),
        "chapters_json": json.dumps(chapters, ensure_ascii=False) if chapters else "",
        "description": description[:1000],
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fetch_error": "",
    }


def error_row(video_id: str | None, original_url: str, error: str) -> dict:
    row = {k: None for k in SCHEMA}
    row.update({
        "video_id": video_id or "",
        "canonical_url": f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
        "original_url": original_url,
        "categories": "",
        "tags": "",
        "subs_manual_langs": "",
        "auto_caption_source_lang": "",
        "has_auto_captions": False,
        "has_chapters": False,
        "chapters_count": 0,
        "chapters_json": "",
        "description": "",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fetch_error": error,
    })
    return row


def load_resume(output_csv: Path) -> tuple[list[dict], set[str]]:
    """Return (existing_rows, set_of_succeeded_video_ids).

    A succeeded row is one with a video_id and an empty fetch_error. pandas reads
    empty CSV cells back as NaN (a float), so we have to handle both NaN and
    empty-string cases — earlier versions only handled the empty-string case and
    refetched everything on restart.
    """
    if not output_csv.exists():
        return [], set()
    prior = pd.read_csv(output_csv)
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


def fetch_one(vid: str, url: str) -> dict:
    """Worker entry point. Always returns a row dict (success or error).

    Keep all exception handling here so the executor never sees a raised future
    and we get a clean per-video error row in the output CSV.
    """
    try:
        return fetch_metadata(vid, url)
    except Exception as e:
        err = str(e).splitlines()[0][:300]
        return error_row(vid, url, err)


def main(
    input_csv: Path,
    output_csv: Path,
    limit: int | None,
    workers: int,
    cookies_from_browser: str | None,
) -> int:
    if not input_csv.exists():
        logging.error(f"input not found: {input_csv}")
        return 2
    if workers < 1:
        logging.error(f"--workers must be >= 1, got {workers}")
        return 2

    if cookies_from_browser:
        global _COOKIES_FROM_BROWSER
        _COOKIES_FROM_BROWSER = (cookies_from_browser,)
        logging.info(f"using cookies from browser: {cookies_from_browser}")

    df = pd.read_csv(input_csv)
    if "links" not in df.columns:
        logging.error(f"{input_csv} has no 'links' column. Columns: {list(df.columns)}")
        return 2

    raw = df["links"].dropna().tolist()
    logging.info(f"loaded {len(raw)} non-null URLs from {input_csv}")

    seen: dict[str, str] = {}  # video_id -> first original URL
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

    todo = [(vid, url) for vid, url in seen.items() if vid not in succeeded]
    if limit is not None:
        todo = todo[:limit]
    logging.info(f"will fetch {len(todo)} videos with {workers} worker(s)")

    rows_by_vid: dict[str, dict] = {
        str(r.get("video_id") or ""): r
        for r in existing_rows
        if str(r.get("video_id") or "")
    }

    rows_lock = threading.Lock()
    completed = 0
    success = 0
    failed = 0
    flush_every = 25

    def flush() -> None:
        # caller holds rows_lock
        df_out = pd.DataFrame(list(rows_by_vid.values()), columns=SCHEMA)
        df_out.to_csv(output_csv, index=False, encoding="utf-8")
        logging.info(f"  flushed {len(df_out)} rows -> {output_csv}")

    if not todo:
        logging.info("nothing to fetch")
        with rows_lock:
            flush()
        return 0

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="ytdl") as pool:
        future_to_vid = {pool.submit(fetch_one, vid, url): vid for vid, url in todo}

        for fut in as_completed(future_to_vid):
            vid = future_to_vid[fut]
            row = fut.result()  # never raises: fetch_one catches everything
            with rows_lock:
                rows_by_vid[vid] = row
                completed += 1
                if row.get("fetch_error"):
                    failed += 1
                    logging.error(
                        f"[{completed}/{len(todo)}] {vid} FAILED: {row['fetch_error']}"
                    )
                else:
                    success += 1
                    title = (row.get("title") or "")[:60]
                    dur = row.get("duration_sec")
                    logging.info(f"[{completed}/{len(todo)}] {vid} ok ({dur}s) {title}")
                if completed % flush_every == 0 or completed == len(todo):
                    flush()

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
    p.add_argument("--workers", type=int, default=8, help="parallel fetch workers")
    p.add_argument(
        "--cookies-from-browser",
        default=None,
        help="browser name (firefox/chrome/edge/brave) — fixes 'Sign in to confirm "
        "you're not a bot' rate-limiting by reusing your real session cookies",
    )
    args = p.parse_args()
    sys.exit(
        main(
            args.input,
            args.output,
            args.limit,
            args.workers,
            args.cookies_from_browser,
        )
    )
