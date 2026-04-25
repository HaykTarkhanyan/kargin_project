"""
Builds a human-readable side-by-side markdown for the Gemini STT spike.

Discovers all model summaries via glob (spike_summary__*.json), so any new
model added via gemini_stt_spike.py --model X automatically shows up.

Sources displayed per video, in order:
  1. Manual hand-curated text from kargin_eng.csv (text + text_common)
  2. YouTube source-lang captions from data/transcripts/*.{lang}.json
  3. Gemini outputs, one block per model
"""

from __future__ import annotations

import glob
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GEM_DIR = ROOT / "data" / "transcripts_gemini"
YT_DIR = ROOT / "data" / "transcripts"
CSV_PATH = ROOT / "kargin_eng.csv"
OUT = GEM_DIR / "comparison.md"

VIDEO_ID_RE = re.compile(r"(?:v=|youtu\.be/)([\w-]{11})")


def yt_url(video_id: str, t_sec: float | None = None) -> str:
    base = f"https://youtu.be/{video_id}"
    return base if t_sec is None else f"{base}?t={int(t_sec)}"


def load_yt(video_id: str) -> dict | None:
    matches = glob.glob(str(YT_DIR / f"*{video_id}.*.json"))
    return json.load(open(matches[0], encoding="utf-8")) if matches else None


def load_manual(df: pd.DataFrame, video_id: str) -> dict:
    row = df[df["video_id"] == video_id]
    if row.empty:
        return {"text": "", "text_common": ""}
    r = row.iloc[0]
    text = "" if pd.isna(r["text"]) else str(r["text"]).strip()
    tc = "" if pd.isna(r["text_common"]) else str(r["text_common"]).strip()
    return {"text": text, "text_common": tc}


def load_csv() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH)
    df["video_id"] = df["links"].apply(
        lambda u: (m.group(1) if (m := VIDEO_ID_RE.search(str(u))) else None)
    )
    return df


def discover_summaries() -> list[dict]:
    summaries = []
    for path in sorted(glob.glob(str(GEM_DIR / "spike_summary__*.json"))):
        s = json.load(open(path, encoding="utf-8"))
        s["_path"] = path
        summaries.append(s)
    return summaries


def render_segments(segments: list[dict]) -> str:
    return "\n".join(
        f"- `{s['start_sec']:6.1f} - {s['end_sec']:6.1f}` {s['text']}"
        for s in segments
    )


def render_yt_events(events: list[dict]) -> str:
    return "\n".join(
        f"- `{e['start']:6.1f} - {e['end']:6.1f}` {e['text']}"
        for e in events
    )


def main() -> None:
    summaries = discover_summaries()
    if not summaries:
        raise SystemExit("no spike_summary__*.json files found; run gemini_stt_spike.py first")

    df = load_csv()
    parts: list[str] = []

    parts.append("# Gemini STT Spike — Side-by-Side\n")
    parts.append("Sources compared per video:")
    parts.append("- **Manual** — hand-curated text from `kargin_eng.csv` (`text` + `text_common`). Often partial or empty.")
    parts.append("- **YouTube** — auto-captions from yt-dlp (`hy-orig` for ground truth videos; foreign-lang garbage for confounders).")
    parts.append("- **Gemini** — one block per model run via `gemini_stt_spike.py --model X`.\n")

    # discovered models summary. Derive gen_sec_sum from per-video records so
    # an idempotent-skip rerun (which collapses summary.wall_sec to ~0) doesn't
    # mislead — gen_sec is preserved per video.
    parts.append("## Models present\n")
    parts.append("| short | model id | spike cost (paid) | n videos | total audio | total gen time |")
    parts.append("|:---|:---|---:|---:|---:|---:|")
    for s in summaries:
        gen_sum = sum(r["gen_sec"] for r in s["per_video"])
        parts.append(
            f"| `{s['model_short']}` | `{s['model']}` | "
            f"${s['total_cost_usd_paid_tier']:.5f} | {s['n_videos']} | "
            f"{s['total_audio_sec']:.0f}s | {gen_sum:.1f}s |"
        )
    parts.append("")

    # full archive extrapolation per model
    parts.append("## Full-archive (33.6h) cost extrapolation per model\n")
    full_archive_sec = 33.6 * 3600
    parts.append("| short | M audio tokens in | M text tokens out | est. cost (paid) | est. wall serial |")
    parts.append("|:---|---:|---:|---:|---:|")
    for s in summaries:
        in_per_sec = s["total_prompt_tokens"] / s["total_audio_sec"]
        out_per_sec = s["total_output_tokens"] / s["total_audio_sec"]
        full_in = in_per_sec * full_archive_sec / 1e6
        full_out = out_per_sec * full_archive_sec / 1e6
        full_cost = full_in * s["audio_in_per_m_usd"] + full_out * s["text_out_per_m_usd"]
        gen_sum = sum(r["gen_sec"] for r in s["per_video"])
        full_wall = gen_sum / s["total_audio_sec"] * full_archive_sec / 60
        parts.append(
            f"| `{s['model_short']}` | {full_in:.2f} | {full_out:.2f} | "
            f"${full_cost:.2f} | {full_wall:.0f} min |"
        )
    parts.append("")

    # per-video metrics table — one row per (video, model)
    parts.append("## Per-video metrics (one row per model run)\n")
    parts.append("| seq | video | cohort | dur (s) | model | gen (s) | tokens in | tokens out | cost paid |")
    parts.append("|---:|:---|:---|---:|:---|---:|---:|---:|---:|")
    # sort by seq for readability
    by_video: dict[str, list[tuple[dict, dict]]] = {}
    for s in summaries:
        for r in s["per_video"]:
            by_video.setdefault(r["video_id"], []).append((s, r))
    # need a stable seq lookup
    seq_lookup = {r["video_id"]: r for s in summaries for r in s["per_video"]}
    ordered_vids = sorted(by_video, key=lambda v: seq_lookup[v]["duration_sec"])

    for vid in ordered_vids:
        for s, r in by_video[vid]:
            files = list(GEM_DIR.glob(f"*_{vid}__{s['model_short']}.json"))
            seq = files[0].name.split("_")[0] if files else "?"
            parts.append(
                f"| {seq} | [`{vid}`]({yt_url(vid)}) | {r['cohort']} | "
                f"{r['duration_sec']:.0f} | `{s['model_short']}` | {r['gen_sec']:.1f} | "
                f"{r['prompt_tokens']} | {r['output_tokens']} | ${r['cost_usd_paid_tier']:.5f} |"
            )
    parts.append("")

    # per-video detailed comparison
    for vid in ordered_vids:
        any_summary, any_row = by_video[vid][0]
        yt = load_yt(vid)
        manual = load_manual(df, vid)
        title = yt["title"] if yt else ""
        title_part = f" — *{title}*" if title else ""

        parts.append(
            f"\n---\n\n## {any_row['cohort']} — [`{vid}`]({yt_url(vid)}) "
            f"({any_row['duration_sec']:.0f}s){title_part}\n"
        )
        parts.append(f"Watch on YouTube: <{yt_url(vid)}>\n")

        if any_row["cohort"] == "hy_orig":
            parts.append("YouTube returned `hy-orig` captions for this video — true ground-truth comparison.\n")
        else:
            yt_lang = any_summary["per_video"][0].get("youtube_source_lang", "?")
            parts.append(f"YouTube STT misidentified this video's source language (intro song fooled the detector). "
                         f"YouTube text is foreign-language garbage; only Gemini and Manual output is meaningful.\n")

        parts.append("### Full text\n")

        # 1. Manual
        if manual["text"] or manual["text_common"]:
            parts.append(f"**Manual — `kargin_eng.csv`:**\n")
            if manual["text"]:
                parts.append(f"_text ({len(manual['text'])} chars):_\n\n> {manual['text']}\n")
            if manual["text_common"]:
                parts.append(f"_text_common ({len(manual['text_common'])} chars):_\n\n> {manual['text_common']}\n")
        else:
            parts.append("**Manual — `kargin_eng.csv`:** (no hand-curated text for this video)\n")

        # 2. YouTube
        if yt:
            parts.append(
                f"**YouTube `{yt['source_lang']}-orig` ({len(yt['full_text'])} chars, {yt['n_events']} events):**\n"
            )
            parts.append(f"> {yt['full_text']}\n")
        else:
            parts.append("**YouTube:** no captions returned for this video.\n")

        # 3. Each Gemini model
        for s, r in by_video[vid]:
            files = list(GEM_DIR.glob(f"*_{vid}__{s['model_short']}.json"))
            if not files:
                continue
            gem = json.load(open(files[0], encoding="utf-8"))
            if gem.get("parse_error"):
                parts.append(f"**Gemini `{s['model_short']}`:** JSON parse error `{gem['parse_error']}`\n")
                parts.append("Raw response:\n```\n" + gem["raw_response_text"][:2000] + "\n```\n")
                continue
            parsed = gem["parsed"]
            parts.append(
                f"**Gemini `{s['model_short']}` ({len(parsed['full_text'])} chars, "
                f"{len(parsed['segments'])} segments):**\n"
            )
            parts.append(f"> {parsed['full_text']}\n")

        # collapsible segments per Gemini model + YouTube events
        parts.append("### Segments\n")
        for s, r in by_video[vid]:
            files = list(GEM_DIR.glob(f"*_{vid}__{s['model_short']}.json"))
            if not files:
                continue
            gem = json.load(open(files[0], encoding="utf-8"))
            if gem.get("parsed"):
                segs = gem["parsed"]["segments"]
                parts.append(
                    f"<details><summary>Gemini `{s['model_short']}` segments ({len(segs)})</summary>\n\n"
                    + render_segments(segs) + "\n\n</details>\n"
                )
        if yt:
            parts.append(
                f"<details><summary>YouTube events ({yt['n_events']})</summary>\n\n"
                + render_yt_events(yt["events"]) + "\n\n</details>\n"
            )

    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
