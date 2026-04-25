"""
Phase-0 Gemini STT spike. Sends 6 hand-picked Kargin audio files to a Gemini
audio-capable model and saves transcripts + cost metadata to data/transcripts_gemini/.

Usage:
  uv run python scripts/gemini_stt_spike.py [--model lite|pro] [video_id_or_seq ...]

Cohorts:
  3 hy-orig videos (varying length)  -> ground truth comparison vs YouTube
  3 wrong-source-lang videos         -> tests "ignore music, transcribe Armenian"

Outputs are namespaced by model so multiple models coexist:
  data/transcripts_gemini/{seq:03d}_{video_id}__{model_short}.json
  data/transcripts_gemini/spike_summary__{model_short}.json
  data/transcripts_gemini/spike__{model_short}.log
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parents[1]
AUDIO_DIR = ROOT / "data" / "audio"
OUT_DIR = ROOT / "data" / "transcripts_gemini"
TMP_DIR = OUT_DIR / "_tmp_ogg"

# paid-tier rates per 1M tokens. pro audio-in price is an estimate (Google's pricing
# page does not list it as of 2026-04-26); pro text-out and lite both confirmed.
MODEL_REGISTRY: dict[str, dict] = {
    "lite": {
        "id": "gemini-3.1-flash-lite-preview",
        "short": "flash-lite",
        "audio_in_per_m": 0.50,
        "text_out_per_m": 1.50,
        "free_tier": True,
    },
    "pro": {
        "id": "gemini-3.1-pro-preview",
        "short": "pro",
        "audio_in_per_m": 2.00,  # estimated; confirm in production
        "text_out_per_m": 12.00,
        "free_tier": False,
    },
}

PROMPT = (
    "Transcribe the Armenian speech in this audio.\n"
    "\n"
    "Rules:\n"
    "1. Transcribe SPEECH ONLY in Armenian script. Do not translate.\n"
    "2. Ignore song lyrics, music, jingles, and background sounds.\n"
    "   The video may open with a Russian or Spanish song before the dialogue starts;\n"
    "   skip it and only transcribe the spoken Armenian dialogue.\n"
    "3. If a section is just music with no Armenian speech, skip it.\n"
    "4. Return strict JSON with this exact shape, no other text:\n"
    '{"full_text": "<all spoken Armenian, joined with spaces>",\n'
    ' "segments": [{"start_sec": <float>, "end_sec": <float>, "text": "<armenian text>"}, ...]}\n'
    "5. Each segment should be one short utterance (one sentence or clause).\n"
    "6. Timestamps are seconds from the start of the audio."
)


@dataclass
class SpikeVideo:
    cohort: str
    video_id: str
    seq: int
    youtube_source_lang: str
    duration_sec: float
    audio_path: Path


PICKS: list[SpikeVideo] = [
    SpikeVideo("hy_orig", "qRZMxJQMlUg", 350, "hy", 75.6,
               AUDIO_DIR / "350_Kargin_Haghordum_sketch_517_Hayko_Mko_qRZMxJQMlUg.webm"),
    SpikeVideo("hy_orig", "uObBR5ju488", 501, "hy", 151.9,
               AUDIO_DIR / "501_Kargin_Haghordum_sketch_129_Hayko_Mko_uObBR5ju488.webm"),
    SpikeVideo("hy_orig", "qjkWGYnwMbw", 70, "hy", 304.4,
               AUDIO_DIR / "070_Kargin_Haghordum_sketch_635_Hayko_Mko_qjkWGYnwMbw.webm"),
    SpikeVideo("confounder", "5h70tn0asdo", 1, "ro", 202.6,
               AUDIO_DIR / "001_Kargin_Haghordum_sketch_275_Hayko_Mko_5h70tn0asdo.webm"),
    SpikeVideo("confounder", "-paMG4kj9gg", 4, "tr", 114.6,
               AUDIO_DIR / "004_Kargin_Haghordum_sketch_278_Hayko_Mko_-paMG4kj9gg.webm"),
    SpikeVideo("confounder", "5F6CLHl2l70", 25, "es", 186.7,
               AUDIO_DIR / "025_Kargin_Haghordum_-_Jorik_Hayko_Mko_5F6CLHl2l70.webm"),
]


def setup_logging(short: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log_path = OUT_DIR / f"spike__{short}.log"
    fmt = "%(asctime)s %(levelname)s %(message)s"
    # reset handlers to avoid duplicate output if called repeatedly
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def transcode_to_ogg(webm_path: Path) -> Path:
    """webm/opus -> ogg/vorbis. Gemini docs list OGG Vorbis as supported, webm is not."""
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    ogg_path = TMP_DIR / (webm_path.stem + ".ogg")
    if ogg_path.exists():
        logging.info(f"transcode skip (cached): {ogg_path.name}")
        return ogg_path
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(webm_path),
        "-vn", "-c:a", "libvorbis", "-q:a", "4",
        str(ogg_path),
    ]
    logging.info(f"transcode: {webm_path.name} -> {ogg_path.name}")
    subprocess.run(cmd, check=True)
    return ogg_path


def cost_usd(prompt_tokens: int, output_tokens: int, model: dict) -> float:
    return (
        (prompt_tokens / 1_000_000) * model["audio_in_per_m"]
        + (output_tokens / 1_000_000) * model["text_out_per_m"]
    )


def run_one(client: genai.Client, video: SpikeVideo, model: dict) -> dict:
    out_path = OUT_DIR / f"{video.seq:03d}_{video.video_id}__{model['short']}.json"
    if out_path.exists():
        logging.info(f"output exists, skipping: {out_path.name}")
        return json.loads(out_path.read_text(encoding="utf-8"))

    if not video.audio_path.exists():
        raise FileNotFoundError(f"missing audio: {video.audio_path}")

    ogg_path = transcode_to_ogg(video.audio_path)

    logging.info(f"upload: {ogg_path.name} ({ogg_path.stat().st_size/1e6:.2f} MB)")
    t_upload = time.perf_counter()
    uploaded = client.files.upload(file=str(ogg_path))
    upload_sec = time.perf_counter() - t_upload

    logging.info(f"generate_content: {video.video_id} (cohort={video.cohort}, dur={video.duration_sec}s, model={model['id']})")
    t_gen = time.perf_counter()
    response = client.models.generate_content(
        model=model["id"],
        contents=[PROMPT, uploaded],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    gen_sec = time.perf_counter() - t_gen

    raw_text = response.text
    parsed = None
    parse_err = None
    try:
        parsed = json.loads(raw_text)
    except Exception as e:
        parse_err = repr(e)
        logging.error(f"JSON parse failed for {video.video_id}: {parse_err}")

    usage = response.usage_metadata
    prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
    output_tokens = getattr(usage, "candidates_token_count", 0) or 0
    total_tokens = getattr(usage, "total_token_count", 0) or 0
    usd = cost_usd(prompt_tokens, output_tokens, model)

    result = {
        "video_id": video.video_id,
        "seq": video.seq,
        "cohort": video.cohort,
        "youtube_source_lang": video.youtube_source_lang,
        "duration_sec": video.duration_sec,
        "model": model["id"],
        "model_short": model["short"],
        "upload_sec": round(upload_sec, 2),
        "gen_sec": round(gen_sec, 2),
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_usd_paid_tier": round(usd, 6),
        "parse_error": parse_err,
        "raw_response_text": raw_text,
        "parsed": parsed,
    }
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    logging.info(
        f"done {video.video_id}: gen={gen_sec:.1f}s tokens={prompt_tokens}+{output_tokens} "
        f"cost=${usd:.5f}"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=list(MODEL_REGISTRY), default="lite",
                        help="model registry key (lite or pro)")
    parser.add_argument("picks", nargs="*",
                        help="optional video_id or seq filters; default = all 6")
    args = parser.parse_args()

    model = MODEL_REGISTRY[args.model]
    setup_logging(model["short"])
    load_dotenv(ROOT / ".env")

    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY not set in .env")

    client = genai.Client()

    if args.picks:
        wanted = set(args.picks)
        videos = [v for v in PICKS if v.video_id in wanted or str(v.seq) in wanted]
        if not videos:
            raise SystemExit(f"no picks matched {wanted}")
    else:
        videos = PICKS

    logging.info(f"running {len(videos)} videos with model={model['id']} (short={model['short']})")
    results = []
    t0 = time.perf_counter()
    for v in videos:
        results.append(run_one(client, v, model))

    total_sec = time.perf_counter() - t0
    total_prompt = sum(r["prompt_tokens"] for r in results)
    total_output = sum(r["output_tokens"] for r in results)
    total_cost = sum(r["cost_usd_paid_tier"] for r in results)
    total_audio = sum(r["duration_sec"] for r in results)

    free_note = "; free tier = $0" if model["free_tier"] else "; no free tier"
    logging.info("=" * 60)
    logging.info(f"summary: {len(results)} videos, {total_audio:.0f}s audio")
    logging.info(f"wall:    {total_sec:.1f}s")
    logging.info(f"tokens:  {total_prompt} in + {total_output} out")
    logging.info(f"cost:    ${total_cost:.5f} (paid tier{free_note})")

    summary_path = OUT_DIR / f"spike_summary__{model['short']}.json"
    summary_path.write_text(
        json.dumps(
            {
                "model": model["id"],
                "model_short": model["short"],
                "free_tier_available": model["free_tier"],
                "audio_in_per_m_usd": model["audio_in_per_m"],
                "text_out_per_m_usd": model["text_out_per_m"],
                "n_videos": len(results),
                "total_audio_sec": total_audio,
                "wall_sec": round(total_sec, 1),
                "total_prompt_tokens": total_prompt,
                "total_output_tokens": total_output,
                "total_cost_usd_paid_tier": round(total_cost, 6),
                "per_video": [
                    {
                        "video_id": r["video_id"],
                        "cohort": r["cohort"],
                        "duration_sec": r["duration_sec"],
                        "gen_sec": r["gen_sec"],
                        "prompt_tokens": r["prompt_tokens"],
                        "output_tokens": r["output_tokens"],
                        "cost_usd_paid_tier": r["cost_usd_paid_tier"],
                        "parse_error": r["parse_error"],
                    }
                    for r in results
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    logging.info(f"summary written: {summary_path}")


if __name__ == "__main__":
    main()
