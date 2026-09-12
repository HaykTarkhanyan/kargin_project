"""
Embed the detailed English summaries from data/text_annotations/ with Gemini
(Vertex AI, $300 GCP credits) and compute sketch-to-sketch similarity.

Artifacts (data/embeddings/):
  summary_vectors.npz     full float32 vectors + video_ids + seqs   (~8.6 MB, local only)
  similarity_matrix.npz   full 702x702 cosine similarity            (~2 MB, local only)
  top_neighbors.json      top-N neighbour ids + scores per sketch   (~50 KB, shippable)

The .npz files are the artifacts of record: neighbour lists can be re-derived at
any N without re-calling the API.

Usage:
  uv run python scripts/embed_annotations.py [--top-n 10] [--dim 3072] [--force]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

ROOT = Path(__file__).resolve().parents[1]
ANNOTATIONS_DIR = ROOT / "data" / "text_annotations"
OUT_DIR = ROOT / "data" / "embeddings"
LEDGER_PATH = ROOT / "data" / "gemini_spend_ledger.jsonl"

MODEL_ID = "gemini-embedding-2"
TEXT_IN_PER_M = 0.15  # USD per 1M input tokens, checked 2026-09-07
TASK_TYPE = "SEMANTIC_SIMILARITY"  # sketch-to-sketch, not query->document


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
            logging.FileHandler(logs_dir / "embed_annotations.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


# 467 of 702 summaries (66.5%) open with a formulaic scene-setting phrase, which
# inflates the similarity floor. The `stripped` variant removes the lead-in phrase
# only - the setting itself (the words after it) is real signal and is kept.
BOILERPLATE_RE = re.compile(
    r"^(?:The sketch (?:takes place|is set|begins|opens|unfolds)"
    r"(?:\s+(?:in|with|at|on|inside|within|during))?|Set in)\s+",
    re.IGNORECASE,
)


def strip_boilerplate(text: str) -> str:
    out = BOILERPLATE_RE.sub("", text, count=1).lstrip()
    return out[0].upper() + out[1:] if out else text


def load_annotations(variant: str) -> list[dict]:
    paths = sorted(ANNOTATIONS_DIR.glob("*__*.json"))
    if not paths:
        raise RuntimeError(f"no annotations found in {ANNOTATIONS_DIR} - run the sweep first")
    docs, stripped = [], 0
    for p in paths:
        d = json.loads(p.read_text(encoding="utf-8"))
        summary = d["annotation"]["summary_detailed_en"].strip()
        if not summary:
            raise RuntimeError(f"empty summary_detailed_en in {p.name}")
        if variant == "stripped":
            new = strip_boilerplate(summary)
            stripped += new != summary
            summary = new
        docs.append({
            "video_id": d["video_id"],
            "seq": d["seq"],
            "title_en": d["annotation"]["title_en"],
            "text": summary,
        })
    if variant == "stripped":
        logging.info(f"boilerplate opener removed from {stripped}/{len(docs)} summaries")
    return docs


RETRYABLE_CODES = {429, 500, 502, 503, 504}
RETRY_BACKOFF_SEC = [5, 15, 45]


def embed_one(client: genai.Client, text: str, dim: int) -> list[float]:
    """One request per document.

    gemini-embedding-2 on Vertex returns exactly ONE embedding regardless of how
    many contents are passed - it silently drops the rest instead of erroring
    (verified 2026-09-07 with batches of 2/4/8). Batching here would misalign
    vectors against video_ids, so the count is asserted on every call.
    """
    for attempt, backoff in enumerate([*RETRY_BACKOFF_SEC, None]):
        try:
            response = client.models.embed_content(
                model=MODEL_ID,
                contents=[text],
                config=types.EmbedContentConfig(task_type=TASK_TYPE, output_dimensionality=dim),
            )
            break
        except genai_errors.APIError as e:
            if e.code in RETRYABLE_CODES and backoff is not None:
                logging.warning(f"API error {e.code}, retry {attempt + 1} in {backoff}s")
                time.sleep(backoff)
                continue
            raise
    if len(response.embeddings) != 1:
        raise RuntimeError(f"expected 1 embedding, got {len(response.embeddings)}")
    values = response.embeddings[0].values
    if len(values) != dim:
        raise RuntimeError(f"expected dim {dim}, got {len(values)}")
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-n", type=int, default=10, help="neighbours per sketch in the JSON")
    parser.add_argument("--dim", type=int, default=3072, choices=[3072, 1536, 768],
                        help="Matryoshka output dimensionality")
    parser.add_argument("--workers", type=int, default=8,
                        help="parallel embedding requests (1 doc per request - see embed_one)")
    parser.add_argument("--variant", choices=["full", "stripped"], default="full",
                        help="full = summaries as written (default, existing artifacts); "
                             "stripped = formulaic scene-setting opener removed")
    parser.add_argument("--force", action="store_true", help="re-embed even if vectors exist")
    args = parser.parse_args()

    setup_logging()
    load_dotenv(ROOT / ".env")
    for var in ("GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_CLOUD_PROJECT"):
        if not os.environ.get(var):
            raise RuntimeError(f"{var} not set in .env - Vertex AI config required")
    os.environ.pop("GEMINI_API_KEY", None)
    os.environ.pop("GOOGLE_API_KEY", None)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sfx = "" if args.variant == "full" else f"__{args.variant}"
    vectors_path = OUT_DIR / f"summary_vectors{sfx}.npz"
    docs = load_annotations(args.variant)
    logging.info(f"loaded {len(docs)} annotations from {ANNOTATIONS_DIR.name} (variant={args.variant})")

    if vectors_path.exists() and not args.force:
        cached = np.load(vectors_path, allow_pickle=False)
        if len(cached["video_ids"]) == len(docs) and cached["vectors"].shape[1] == args.dim:
            logging.info(f"vectors exist and match ({vectors_path.name}), skipping embedding; "
                         f"use --force to re-embed")
            vectors = cached["vectors"]
            video_ids = list(cached["video_ids"])
            seqs = list(cached["seqs"])
            titles = list(cached["titles"])
        else:
            raise RuntimeError(
                f"{vectors_path.name} exists but does not match current data "
                f"({len(cached['video_ids'])} vecs dim {cached['vectors'].shape[1]} vs "
                f"{len(docs)} docs dim {args.dim}) - pass --force to rebuild"
            )
    else:
        client = genai.Client()
        all_vecs: list[list[float] | None] = [None] * len(docs)
        done = 0
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(embed_one, client, d["text"], args.dim): i
                       for i, d in enumerate(docs)}
            for fut in as_completed(futures):
                all_vecs[futures[fut]] = fut.result()  # raises loudly on any failure
                done += 1
                if done % 100 == 0 or done == len(docs):
                    logging.info(f"embedded {done}/{len(docs)}")
        wall = time.perf_counter() - t0

        if any(v is None for v in all_vecs):
            raise RuntimeError("some embeddings missing after run")
        vectors = np.asarray(all_vecs, dtype=np.float32)
        video_ids = [d["video_id"] for d in docs]
        seqs = [d["seq"] for d in docs]
        titles = [d["title_en"] for d in docs]

        # Truncated Matryoshka vectors are not unit-norm; normalize so cosine == dot.
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        if (norms == 0).any():
            raise RuntimeError("zero-norm embedding returned")
        vectors = vectors / norms

        np.savez_compressed(vectors_path, vectors=vectors, video_ids=np.array(video_ids),
                            seqs=np.array(seqs), titles=np.array(titles),
                            model=np.array(MODEL_ID), task_type=np.array(TASK_TYPE))
        est_tokens = sum(len(d["text"]) for d in docs) / 4
        usd = (est_tokens / 1_000_000) * TEXT_IN_PER_M
        with LEDGER_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
                "script": "embed_annotations", "model": MODEL_ID, "variant": args.variant, "n_docs": len(docs),
                "dim": args.dim, "est_prompt_tokens": int(est_tokens),
                "cost_usd": round(usd, 6), "note": "token count estimated from chars/4",
            }, ensure_ascii=False) + "\n")
        logging.info(f"embedded {len(docs)} docs in {wall:.1f}s, dim={args.dim}, "
                     f"~{int(est_tokens)} tokens, est ${usd:.4f} -> {vectors_path.name}")

    # cosine similarity on normalized vectors == dot product
    sim = vectors @ vectors.T
    np.fill_diagonal(sim, -np.inf)  # never a sketch's own neighbour
    np.savez_compressed(OUT_DIR / f"similarity_matrix{sfx}.npz",
                        similarity=sim.astype(np.float32), video_ids=np.array(video_ids))
    logging.info(f"similarity matrix {sim.shape} -> similarity_matrix{sfx}.npz")

    order = np.argsort(-sim, axis=1)[:, :args.top_n]
    neighbors = {
        video_ids[i]: [[video_ids[j], round(float(sim[i, j]), 4)] for j in order[i]]
        for i in range(len(docs))
    }
    (OUT_DIR / f"top_neighbors{sfx}.json").write_text(json.dumps({
        "model": MODEL_ID, "dim": args.dim, "task_type": TASK_TYPE, "top_n": args.top_n,
        "variant": args.variant,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "format": "video_id -> [[neighbor_video_id, cosine], ...] descending",
        "neighbors": neighbors,
    }, ensure_ascii=False), encoding="utf-8")
    size_kb = (OUT_DIR / f"top_neighbors{sfx}.json").stat().st_size / 1024
    logging.info(f"top-{args.top_n} neighbours -> top_neighbors{sfx}.json ({size_kb:.0f} KB)")

    logging.info("=" * 60)
    logging.info("sample neighbours (eyeball these):")
    title_by_id = dict(zip(video_ids, titles))
    for i in [0, len(docs) // 3, 2 * len(docs) // 3]:
        logging.info(f"  [{seqs[i]}] {titles[i]}")
        for nid, score in neighbors[video_ids[i]][:3]:
            logging.info(f"       {score:.3f}  {title_by_id[nid]}")


if __name__ == "__main__":
    main()
