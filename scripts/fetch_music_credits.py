"""Scrape the public "Music / Suggested by" panel off each video's watch page.

This is the only public surface for music copyright information on videos you
don't own. The Data API v3 has no field for it, and yt-dlp returns 78 fields
for these videos with nothing music- or licence-related among them. Content ID
claims proper live behind the partner-only Content ID API.

What IS public: YouTube renders identified music under the description as rows
like

    Suggested by SME -> Henry Mancini - The Pink Panther Theme (Official Audio)
    Song / Artist / Album / Licensed to YouTube by -> ...

Those rows sit in ytInitialData at

    contents.twoColumnWatchNextResults.results.results.contents[]
      .videoSecondaryInfoRenderer.metadataRowContainer.metadataRowContainerRenderer.rows

`metadataRowContainer` is a GENERIC label->value container that YouTube reuses
for music, games, and other attributions, and the label set varies by video and
locale. So this captures every row verbatim into `rows_json` rather than
hunting for a "Song" key -- hard-coding the labels would have missed the
"Suggested by SME" shape that these videos actually use. The flattened
convenience columns are derived from those rows, never a substitute for them.

Bandwidth note: a watch page is ~1.2-1.7 MB, but ytInitialData sits well before
the end, so the response is streamed and dropped as soon as that blob closes.

Resume-safe: video_ids already in the output CSV are skipped.

Usage:
    uv run python scripts/fetch_music_credits.py
    uv run python scripts/fetch_music_credits.py --limit 5      # smoke test
    uv run python scripts/fetch_music_credits.py --sleep 1.5    # be politer
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "fetch_music_credits.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
INIT_DATA = re.compile(r"var ytInitialData\s*=\s*(\{.*?\});</script>", re.S)
MAX_BYTES = 3_000_000          # hard stop; ytInitialData is far earlier than this
FAILURE_STREAK_LIMIT = 10      # consecutive failures that mean "we're blocked"

SCHEMA = [
    "video_id", "has_music_rows", "row_count",
    "claim_labels",     # e.g. "Suggested by SME"
    "claim_values",     # e.g. "Henry Mancini - The Pink Panther Theme ..."
    "linked_video_ids",  # rows often link to the official track's video
    "rows_json",        # every row verbatim: the source of truth
    "fetched_at", "fetch_error",
]

# Labels that indicate music attribution. Used ONLY to set the convenience
# boolean; every row is stored regardless of whether it matches.
MUSIC_HINTS = ("music", "song", "artist", "album", "licensed", "suggested",
               "provided to youtube", "composer", "writer", "label")


def find_rows(node):
    """Every metadataRowContainerRenderer.rows list anywhere in ytInitialData."""
    if isinstance(node, dict):
        if "metadataRowContainerRenderer" in node:
            rows = node["metadataRowContainerRenderer"].get("rows")
            if rows:
                yield rows
        for v in node.values():
            yield from find_rows(v)
    elif isinstance(node, list):
        for v in node:
            yield from find_rows(v)


def text_of(node) -> str:
    """Flatten a YouTube text node (simpleText or runs) to a plain string."""
    if not isinstance(node, dict):
        return ""
    if "simpleText" in node:
        return str(node["simpleText"])
    return "".join(str(r.get("text", "")) for r in node.get("runs") or [])


def video_ids_in(node) -> list[str]:
    """videoIds referenced by a row -- rows link to the official track upload."""
    out = []
    if isinstance(node, dict):
        if isinstance(node.get("videoId"), str):
            out.append(node["videoId"])
        for v in node.values():
            out.extend(video_ids_in(v))
    elif isinstance(node, list):
        for v in node:
            out.extend(video_ids_in(v))
    return out


def parse_rows(rows) -> list[dict]:
    """[{label, values, video_ids}] from a metadataRowContainerRenderer rows list."""
    parsed = []
    for row in rows:
        # Two shapes appear: metadataRowRenderer (label + contents) and
        # metadataRowHeaderRenderer (a section heading like "Music").
        renderer = row.get("metadataRowRenderer") or row.get("metadataRowHeaderRenderer")
        if not renderer:
            continue
        label = text_of(renderer.get("title") or {})
        contents = renderer.get("contents") or []
        values = [text_of(c) for c in contents] if contents else []
        if not values and (c := renderer.get("content")):
            values = [text_of(c)]
        values = [v for v in values if v.strip()]
        parsed.append({
            "label": label,
            "values": values,
            "video_ids": sorted(set(video_ids_in(renderer))),
        })
    return parsed


def fetch_page(session: requests.Session, video_id: str) -> str:
    """Watch page HTML, streamed only until ytInitialData is complete."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    with session.get(url, timeout=30, stream=True) as r:
        r.raise_for_status()
        if "consent" in r.url:
            raise RuntimeError(f"redirected to a consent wall: {r.url}")
        buf = []
        size = 0
        for chunk in r.iter_content(chunk_size=65536, decode_unicode=True):
            if not chunk:
                continue
            buf.append(chunk)
            size += len(chunk)
            # Cheap check: only join once the terminator could plausibly be present.
            if ";</script>" in chunk:
                html = "".join(buf)
                if INIT_DATA.search(html):
                    return html
            if size > MAX_BYTES:
                break
        return "".join(buf)


def scrape_one(session: requests.Session, video_id: str) -> dict:
    html = fetch_page(session, video_id)
    m = INIT_DATA.search(html)
    if not m:
        raise RuntimeError("ytInitialData not found in page")
    data = json.loads(m.group(1))

    rows: list[dict] = []
    for group in find_rows(data):
        rows.extend(parse_rows(group))

    music = [r for r in rows if any(h in r["label"].lower() for h in MUSIC_HINTS)]
    linked = sorted({v for r in rows for v in r["video_ids"]})
    return {
        "video_id": video_id,
        "has_music_rows": bool(music),
        "row_count": len(rows),
        "claim_labels": " | ".join(r["label"] for r in rows if r["label"]),
        "claim_values": " | ".join(v for r in rows for v in r["values"]),
        "linked_video_ids": ",".join(linked),
        "rows_json": json.dumps(rows, ensure_ascii=False),
        "fetched_at": pd.Timestamp.now("UTC").isoformat(timespec="seconds"),
        "fetch_error": "",
    }


def main(input_csv: Path, out_path: Path, limit: int | None, sleep_sec: float) -> int:
    ids = pd.read_csv(input_csv)["video_id"].dropna().astype(str).tolist()
    logging.info(f"{len(ids)} videos in {input_csv}")

    done: dict[str, dict] = {}
    if out_path.exists():
        prior = pd.read_csv(out_path)
        for col in SCHEMA:
            if col not in prior.columns:
                prior[col] = ""
        # Only rows that actually succeeded count as done; failures get retried.
        for r in prior[SCHEMA].to_dict("records"):
            if str(r.get("fetch_error") or "").strip() in ("", "nan"):
                done[str(r["video_id"])] = r
        logging.info(f"resume: {len(done)} already scraped")

    todo = [v for v in ids if v not in done]
    if limit is not None:
        todo = todo[:limit]
    logging.info(f"{len(todo)} to scrape (sleep {sleep_sec}s between requests)")
    if not todo:
        logging.info("nothing to do")
        return 0

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"})

    rows_out = dict(done)
    ok = fail = with_music = 0
    consecutive_failures = 0
    for i, vid in enumerate(todo, 1):
        try:
            row = scrape_one(session, vid)
            ok += 1
            consecutive_failures = 0
            if row["has_music_rows"]:
                with_music += 1
                logging.info(f"[{i}/{len(todo)}] {vid} MUSIC: {row['claim_labels']} -> {row['claim_values'][:100]}")
        except Exception as e:
            fail += 1
            consecutive_failures += 1
            msg = f"{type(e).__name__}: {str(e).splitlines()[0][:200]}"
            logging.error(f"[{i}/{len(todo)}] {vid} failed: {msg}")
            row = {k: "" for k in SCHEMA}
            row.update({"video_id": vid, "has_music_rows": False, "row_count": 0,
                        "fetched_at": pd.Timestamp.now("UTC").isoformat(timespec="seconds"),
                        "fetch_error": msg})
        rows_out[vid] = row

        # If YouTube starts blocking, every remaining request will fail the same
        # way. Stop instead of burning through hundreds of them; the run is
        # resume-safe, so a later re-run picks up exactly where this left off.
        if consecutive_failures >= FAILURE_STREAK_LIMIT:
            logging.error(
                f"{consecutive_failures} consecutive failures -- stopping early "
                f"(likely rate-limited). Re-run later to resume."
            )
            break

        if i % 25 == 0 or i == len(todo):
            logging.info(f"[{i}/{len(todo)}] progress: {ok} ok, {fail} fail, {with_music} with music rows")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(list(rows_out.values()), columns=SCHEMA).to_csv(out_path, index=False, encoding="utf-8")
        if sleep_sec > 0 and i < len(todo):
            time.sleep(sleep_sec)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(list(rows_out.values()), columns=SCHEMA).to_csv(out_path, index=False, encoding="utf-8")
    logging.info(f"done. {ok} ok, {fail} fail, {with_music} with music rows -> {out_path}")
    return 1 if fail else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", default=Path("data/youtube_metadata.csv"), type=Path)
    p.add_argument("--out", default=Path("data/music_credits.csv"), type=Path)
    p.add_argument("--limit", type=int, default=None, help="for smoke testing")
    p.add_argument("--sleep", type=float, default=1.0, help="seconds between requests")
    args = p.parse_args()
    sys.exit(main(args.input, args.out, args.limit, args.sleep))
