"""
Extract search/browse annotation columns from Kargin sketch texts with Gemini
(structured output via response_schema). Runs on Vertex AI ($300 GCP credits),
NOT the GEMINI_API_KEY developer-API path.

Input per sketch: title + curated text/text_common from kargin_eng.csv + the
YouTube transcript (data/transcripts/{seq:03d}_*.hy.json) when one exists.

Usage:
  uv run python scripts/extract_text_annotations.py --model flash3 [--out-dir DIR] [--limit N] [picks ...]

picks are video_ids or seqs. Outputs are namespaced by model so multiple
models coexist (same convention as gemini_stt_spike.py):
  {out_dir}/{seq:03d}_{video_id}__{model_short}.json

Every call appends one line to data/gemini_spend_ledger.jsonl (per-call cost
ledger shared by all Gemini scripts in this repo).
"""

from __future__ import annotations

import argparse
import enum
import json
import logging
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
KARGIN_CSV = ROOT / "kargin_eng.csv"
METADATA_CSV = ROOT / "data" / "youtube_metadata.csv"
TRANSCRIPTS_DIR = ROOT / "data" / "transcripts"
VISUALS_DIR = ROOT / "data" / "visual_annotations"
DEFAULT_OUT_DIR = ROOT / "data" / "text_annotations"
LEDGER_PATH = ROOT / "data" / "gemini_spend_ledger.jsonl"

# paid-tier rates per 1M tokens, checked 2026-09-07 (Vertex; 3.8-flash is
# intro pricing through 2026-12-31, doubles to 1.50/7.50 from 2027-01-01).
# Thinking tokens bill at the output rate on Gemini 3 models.
MODEL_REGISTRY: dict[str, dict] = {
    "flash3": {
        "id": "gemini-3-flash-preview",
        "short": "flash3",
        "text_in_per_m": 0.50,
        "text_out_per_m": 3.00,
    },
    "flash38": {
        "id": "gemini-3.8-flash",
        "short": "flash38",
        "text_in_per_m": 0.75,
        "text_out_per_m": 3.75,
    },
}


class Topic(str, enum.Enum):
    family = "family"
    work = "work"
    money = "money"
    police = "police"
    medical = "medical"
    village = "village"
    shop_market = "shop_market"
    school = "school"
    law_court = "law_court"
    army = "army"
    transport = "transport"
    romance = "romance"
    drinking = "drinking"
    restaurant_cafe = "restaurant_cafe"
    crime = "crime"
    neighbors = "neighbors"
    bureaucracy = "bureaucracy"
    media_tv = "media_tv"
    sports = "sports"
    religion = "religion"
    other = "other"


class HumorType(str, enum.Enum):
    wordplay = "wordplay"
    absurd = "absurd"
    situational = "situational"
    character = "character"
    satire = "satire"
    slapstick = "slapstick"
    misunderstanding = "misunderstanding"
    dark = "dark"
    other = "other"


class Annotation(BaseModel):
    title_hy: str
    title_en: str
    summary_en: str
    summary_detailed_en: str
    keywords_hy: list[str]
    keywords_en: list[str]
    keywords_translit: list[str]
    catchphrases: list[str]
    topics: list[Topic]
    humor_type: list[HumorType]


PROMPT_HEADER = """\
You annotate sketches from "Kargin Haghordum", the Armenian comedy series by
Hayko and Mko: short (1-5 min) dialogue sketches in colloquial Eastern Armenian,
often with Russian loanwords.

You get whatever exists for one sketch: the (generic) YouTube title,
hand-curated dialogue fragments (often PARTIAL, sometimes just a few remembered
lines), recurring catchphrases, sometimes an auto-generated YouTube transcript
(may contain recognition errors), and a VISUAL ANNOTATION extracted from the
video frames (setting, characters, props - reliable for what is on screen, but
it cannot hear the dialogue). Combine text and visuals. Extract:

- title_hy: a short distinctive Armenian title for this sketch (2-5 words),
  like an episode title - specific to its premise, not generic.
- title_en: the same title idea in English (2-5 words).
- summary_en: 1-2 sentence English summary of the sketch's premise/joke.
- summary_detailed_en: 120-200 word English description covering EVERY scene in
  order: the setting, who the characters are (note when a character is a woman
  played by one of the male comedians in drag - a running feature of the show -
  but never guess WHICH comedian plays which role; the data does not say), what
  happens, the jokes, and the closing punchline. Weave in visual details
  (costumes, props, location) where they add substance. Write it as a
  standalone description - it will be used for semantic search.
- keywords_hy: 5-12 Armenian-script search keywords/phrases.
- keywords_en: 5-12 English search keywords/phrases.
- keywords_translit: the keywords_hy list transliterated to Latin script the
  way Armenians type informally (e.g. "barev", "inch ka", "aper").
- catchphrases: 0-5 verbatim quotable lines in Armenian script, copied exactly
  from the provided text. Only genuinely punchy/memorable lines; empty list if none.
- topics: 1-3 from the fixed vocabulary.
- humor_type: 1-2 from the fixed vocabulary.

Do not invent content that is not supported by the given text or visuals.
"""


def setup_logging() -> None:
    logs_dir = ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(logs_dir / "extract_text_annotations.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def load_rows() -> pd.DataFrame:
    """Join curation CSV with metadata; seq = 1-based youtube_metadata row order
    (matches the NNN_ prefix used by every per-video file in data/)."""
    kargin = pd.read_csv(KARGIN_CSV)
    meta = pd.read_csv(METADATA_CSV)
    meta["seq"] = range(1, len(meta) + 1)
    rows = meta[["seq", "video_id", "title"]].merge(kargin, on="video_id", how="left")
    if rows["id"].isna().any():
        missing = rows[rows["id"].isna()]["video_id"].tolist()
        raise RuntimeError(f"metadata videos missing from kargin_eng.csv: {missing[:5]}...")
    return rows


def find_transcript(seq: int) -> tuple[str | None, str | None]:
    """Return (full_text, filename). Prefer the Armenian (.hy.json) transcript."""
    hy = sorted(TRANSCRIPTS_DIR.glob(f"{seq:03d}_*.hy.json"))
    any_lang = sorted(TRANSCRIPTS_DIR.glob(f"{seq:03d}_*.json"))
    path = hy[0] if hy else (any_lang[0] if any_lang else None)
    if path is None:
        return None, None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("full_text"), path.name


def format_visual(seq: int, video_id: str) -> str | None:
    path = VISUALS_DIR / f"{seq:03d}_{video_id}.json"
    if not path.exists():
        return None
    v = json.loads(path.read_text(encoding="utf-8"))
    lines = [
        f"location: {v.get('location_fine')} ({v.get('indoor_outdoor')}, {v.get('day_night')})",
        f"characters seen: {', '.join(v.get('character_types', []))}",
        f"male actors playing female roles (drag): {v.get('drag')}",
    ]
    if v.get("animals"):
        lines.append(f"animals: {', '.join(v['animals'])}")
    if v.get("key_props"):
        lines.append(f"props: {', '.join(v['key_props'])}")
    lines.append(f"physicality: {v.get('physicality')}, distinct settings: {v.get('scene_structure', {}).get('settings')}")
    lines.append(f"visual synopsis: {v.get('visual_synopsis')}")
    return "\n".join(lines)


def build_input(row: pd.Series) -> tuple[str, dict]:
    seq, video_id = int(row["seq"]), row["video_id"]
    transcript_text, transcript_file = find_transcript(seq)
    visual = format_visual(seq, video_id)
    parts = [f"TITLE: {row['title']}"]
    sources = {"title": True, "text": False, "text_common": False,
               "transcript": transcript_file, "visual": visual is not None}
    if isinstance(row.get("text"), str) and row["text"].strip():
        parts.append(f"CURATED DIALOGUE (may be partial):\n{row['text'].strip()}")
        sources["text"] = True
    if isinstance(row.get("text_common"), str) and row["text_common"].strip():
        parts.append(f"CURATED CATCHPHRASES:\n{row['text_common'].strip()}")
        sources["text_common"] = True
    if transcript_text:
        parts.append(f"YOUTUBE TRANSCRIPT (auto-generated, may have errors):\n{transcript_text.strip()}")
    if visual:
        parts.append(f"VISUAL ANNOTATION (from video frames):\n{visual}")
    return "\n\n".join(parts), sources


def cost_usd(prompt_tokens: int, output_tokens: int, thoughts_tokens: int, model: dict) -> float:
    return (
        (prompt_tokens / 1_000_000) * model["text_in_per_m"]
        + ((output_tokens + thoughts_tokens) / 1_000_000) * model["text_out_per_m"]
    )


_ledger_lock = threading.Lock()
RETRYABLE_CODES = {429, 500, 502, 503, 504}
RETRY_BACKOFF_SEC = [5, 15, 45]


def append_ledger(entry: dict) -> None:
    with _ledger_lock:
        with LEDGER_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def generate_with_retry(client: genai.Client, model_id: str, contents: list,
                        config: types.GenerateContentConfig):
    for attempt, backoff in enumerate([*RETRY_BACKOFF_SEC, None]):
        try:
            return client.models.generate_content(model=model_id, contents=contents, config=config)
        except genai_errors.APIError as e:
            if e.code in RETRYABLE_CODES and backoff is not None:
                logging.warning(f"API error {e.code}, retry {attempt + 1} in {backoff}s: {e.message}")
                time.sleep(backoff)
                continue
            raise


def run_one(client: genai.Client, row: pd.Series, model: dict, out_dir: Path,
            thinking_config: types.ThinkingConfig | None = None) -> dict:
    seq, video_id = int(row["seq"]), row["video_id"]
    out_path = out_dir / f"{seq:03d}_{video_id}__{model['short']}.json"
    if out_path.exists():
        try:
            cached = json.loads(out_path.read_text(encoding="utf-8"))
            logging.info(f"output exists, skipping: {out_path.name}")
            return cached
        except json.JSONDecodeError:
            logging.warning(f"corrupt output, regenerating: {out_path.name}")

    input_text, sources = build_input(row)
    logging.info(
        f"generate: seq={seq} video={video_id} model={model['id']} "
        f"input_chars={len(input_text)} transcript={sources['transcript']}"
    )
    t0 = time.perf_counter()
    response = generate_with_retry(
        client,
        model["id"],
        [PROMPT_HEADER, input_text],
        types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Annotation,
            thinking_config=thinking_config,
        ),
    )
    gen_sec = time.perf_counter() - t0

    annotation: Annotation = response.parsed
    if annotation is None:
        finish = response.candidates[0].finish_reason if response.candidates else None
        raise RuntimeError(
            f"no parsed structured output for seq={seq}: finish_reason={finish}, "
            f"prompt_feedback={response.prompt_feedback}, text={(response.text or '')[:300]!r}"
        )

    usage = response.usage_metadata
    prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
    output_tokens = getattr(usage, "candidates_token_count", 0) or 0
    thoughts_tokens = getattr(usage, "thoughts_token_count", 0) or 0
    usd = cost_usd(prompt_tokens, output_tokens, thoughts_tokens, model)

    result = {
        "video_id": video_id,
        "seq": seq,
        "kargin_id": int(row["id"]),
        "title": row["title"],
        "model": model["id"],
        "model_short": model["short"],
        "schema_version": 2,
        "input_sources": sources,
        "input_chars": len(input_text),
        "gen_sec": round(gen_sec, 2),
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "thoughts_tokens": thoughts_tokens,
        "cost_usd": round(usd, 6),
        "annotation": annotation.model_dump(mode="json"),
    }
    tmp_path = out_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, out_path)
    append_ledger({
        "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
        "script": "extract_text_annotations",
        "model": model["id"],
        "seq": seq,
        "video_id": video_id,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "thoughts_tokens": thoughts_tokens,
        "cost_usd": round(usd, 6),
    })
    logging.info(
        f"done seq={seq}: gen={gen_sec:.1f}s tokens={prompt_tokens}+{output_tokens}"
        f"(+{thoughts_tokens} thinking) cost=${usd:.5f}"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=list(MODEL_REGISTRY), required=True)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--limit", type=int, default=None,
                        help="process at most N rows (after picks filter)")
    parser.add_argument("--thinking", choices=["off", "minimal"], default=None,
                        help="override thinking: off = thinking_budget 0, minimal = thinking_level MINIMAL; default = model default")
    parser.add_argument("--workers", type=int, default=1,
                        help="parallel API calls (thread pool); 1 = sequential")
    parser.add_argument("picks", nargs="*", help="video_id or seq filters")
    args = parser.parse_args()

    model = dict(MODEL_REGISTRY[args.model])
    thinking_config = None
    if args.thinking == "off":
        thinking_config = types.ThinkingConfig(thinking_budget=0)
        model["short"] += "-nothink"
    elif args.thinking == "minimal":
        thinking_config = types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL)
        model["short"] += "-minthink"
    setup_logging()
    load_dotenv(ROOT / ".env")
    for var in ("GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_CLOUD_PROJECT"):
        if not os.environ.get(var):
            raise RuntimeError(f"{var} not set in .env - Vertex AI config required")
    # Force the Vertex path even though GEMINI_API_KEY is also in .env:
    # the credits are on the GCP project, not the AI Studio key.
    os.environ.pop("GEMINI_API_KEY", None)
    os.environ.pop("GOOGLE_API_KEY", None)

    client = genai.Client()
    rows = load_rows()

    if args.picks:
        wanted = set(args.picks)
        rows = rows[rows["video_id"].isin(wanted) | rows["seq"].astype(str).isin(wanted)]
        if rows.empty:
            raise SystemExit(f"no rows matched {wanted}")
    if args.limit is not None:
        rows = rows.head(args.limit)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    logging.info(f"running {len(rows)} rows with model={model['id']} "
                 f"workers={args.workers} -> {args.out_dir}")
    results: list[dict] = []
    failures: list[tuple[int, str]] = []

    def safe_run(row: pd.Series) -> None:
        try:
            results.append(run_one(client, row, model, args.out_dir, thinking_config))
        except Exception as e:
            logging.error(f"FAILED seq={row['seq']} video={row['video_id']}: {e}")
            failures.append((int(row["seq"]), str(e)))

    row_list = [row for _, row in rows.iterrows()]
    if args.workers <= 1:
        for row in row_list:
            safe_run(row)
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(safe_run, row) for row in row_list]
            for f in as_completed(futures):
                f.result()

    total_cost = sum(r["cost_usd"] for r in results)
    total_in = sum(r["prompt_tokens"] for r in results)
    total_out = sum(r["output_tokens"] + r["thoughts_tokens"] for r in results)
    logging.info("=" * 60)
    logging.info(f"summary: {len(results)}/{len(row_list)} rows ok, tokens {total_in} in + {total_out} out, "
                 f"cost ${total_cost:.5f} (ledger: {LEDGER_PATH.name})")
    if failures:
        for seq, err in sorted(failures):
            logging.error(f"failed seq={seq}: {err[:200]}")
        logging.error(f"{len(failures)} rows FAILED - rerun the same command to retry just those")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
