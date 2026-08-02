"""Select the videos that still need a transcript and build a batch manifest.

Why this exists
---------------
618 of 702 videos have no usable Armenian transcript. YouTube's ASR handles
Armenian well (the `hy` captions we already hold are clean), but its language
auto-detection frequently guesses wrong on this audio -- 92 videos came back as
Turkish, 48 as English, 24 as Russian -- and a wrong guess produces either
nothing but [Muzik] markers or outright phonetic hallucination.

Uploading the audio ourselves fixes that, because the uploader sets
`defaultAudioLanguage` explicitly instead of letting detection guess.

This script does the SELECTION and the OFFSET TABLE only. Rendering is a
separate step (render_transcription_batch.py) so the expensive part never runs
by accident.

The offset table is the important output. Captions are timestamped, so once the
clips are concatenated in a known order with known durations, splitting the
returned transcript back into per-video pieces is arithmetic -- no marker
parsing, no alignment heuristics. Durations are probed from the actual audio
files, never taken from YouTube metadata, because the concatenation is built
from those files and any disagreement would desynchronise every later clip.

Usage:
    uv run python scripts/build_transcription_batch.py
    uv run python scripts/build_transcription_batch.py --out data/transcription_batch
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "build_transcription_batch.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

# The only caption language we treat as usable. Everything else in the archive
# is either empty ([Muzik] markers) or phonetic nonsense produced by ASR running
# the wrong acoustic model against Armenian speech.
USABLE_LANG = "hy"


def caption_lang(transcripts_raw: Path) -> dict[str, str]:
    """video_id -> detected caption language, or NONE when yt-dlp found none.

    Filenames look like `001_Some_Title_VIDEOID.hy-orig.json3` or
    `002_Some_Title_VIDEOID.no_captions`. Titles contain underscores and video
    ids may themselves contain `_` and `-`, so the id is taken as the last 11
    characters of the stem rather than by splitting on a separator.
    """
    out: dict[str, str] = {}
    for p in transcripts_raw.iterdir():
        stem, _, ext = p.name.partition(".")
        out[stem[-11:]] = "NONE" if ext == "no_captions" else ext.split("-")[0]
    return out


def audio_paths(audio_dir: Path) -> dict[str, Path]:
    """video_id -> audio file, using the same trailing-11-chars rule."""
    return {p.stem[-11:]: p for p in audio_dir.iterdir() if p.is_file()}


def probe_duration(path: Path) -> float:
    """Exact stream duration in seconds, from the file itself.

    Fails loudly: a missing or unparseable duration would silently shift every
    subsequent clip's offset, which is the one error that would quietly corrupt
    the whole batch.
    """
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", str(path)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {path.name}: {proc.stderr.strip()}")
    dur = json.loads(proc.stdout).get("format", {}).get("duration")
    if dur is None:
        raise RuntimeError(f"ffprobe reported no duration for {path.name}")
    return float(dur)


def already_batched(manifests: list[Path]) -> set[str]:
    """video_ids covered by manifests already built, so batches never overlap."""
    seen: set[str] = set()
    for m in manifests:
        if not m.exists():
            raise RuntimeError(f"--exclude manifest not found: {m}")
        seen.update(pd.read_csv(m, dtype=str)["video_id"])
    return seen


def split_balanced(picked: pd.DataFrame, n: int) -> list[pd.DataFrame]:
    """Split into n contiguous chunks of roughly equal RUNTIME, not equal count.

    Contiguous so each batch stays in curation-id order, which keeps its chapter
    list readable. Balanced by duration rather than clip count because the
    durations are so uneven -- one 19.6 min clip against a 3.4 min median -- that
    equal counts would produce very unequal uploads.
    """
    target = picked["duration_sec"].sum() / n
    chunks, current, run = [], [], 0.0
    for row in picked.itertuples():
        current.append(row.Index)
        run += row.duration_sec
        # Close the chunk once past the target, unless this is the last chunk
        # (everything remaining belongs to it) or too few clips are left to fill
        # the chunks still owed.
        remaining = len(picked) - len(current) - sum(len(c) for c in chunks)
        if run >= target and len(chunks) < n - 1 and remaining > (n - len(chunks) - 1):
            chunks.append(current)
            current, run = [], 0.0
    if current:
        chunks.append(current)
    return [picked.loc[idx] for idx in chunks]


ARMENIAN = re.compile(r"[԰-֏]")

# A transcript this size is doing its job; anything less is noise or silence.
GOOD_TRANSCRIPT_CHARS = 500


def has_good_transcript(transcripts_dir: Path) -> set[str]:
    """video_ids already holding a usable Armenian transcript, from any source.

    Checked against the transcripts on disk rather than against caption-language
    filenames, because after a batch round a video may have a fine transcript
    that YouTube's own page never carried.
    """
    out = set()
    if not transcripts_dir.exists():
        return out
    for p in transcripts_dir.glob("*.hy.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        if len(ARMENIAN.findall(d.get("full_text") or "")) >= GOOD_TRANSCRIPT_CHARS:
            out.add(d.get("video_id"))
    return out


def select(source: Path, transcripts_raw: Path, audio_dir: Path,
           exclude: list[Path], max_words: int, transcripts_dir: Path) -> pd.DataFrame:
    """Videos whose dialogue is missing or thin AND that lack a good transcript.

    `max_words` is the ceiling on curated dialogue. 0 means "nothing curated at
    all", which selected the first 87. Raising it reaches videos with token
    curation -- measured worthwhile only up to about 50 words, because beyond
    that curation already runs ~95% the length of what ASR would return, and a
    transcript would duplicate it more noisily rather than add anything.
    """
    df = pd.read_csv(source, dtype=str, keep_default_na=False)
    df["words"] = df["text"].str.split().str.len()
    df["caption_lang"] = df["video_id"].map(caption_lang(transcripts_raw)).fillna("MISSING")

    done = has_good_transcript(transcripts_dir)
    picked = df[(df["words"] <= max_words) & (~df["video_id"].isin(done))].copy()
    logging.info(f"{len(picked)} with <={max_words} curated words and no transcript "
                 f"(of {len(df)}; {len(done)} already have one)")

    if exclude:
        done = already_batched(exclude)
        before = len(picked)
        picked = picked[~picked["video_id"].isin(done)]
        logging.info(f"excluded {before - len(picked)} already covered by "
                     f"{len(exclude)} earlier manifest(s)")

    paths = audio_paths(audio_dir)
    missing = [v for v in picked["video_id"] if v not in paths]
    if missing:
        raise RuntimeError(f"no audio file for {len(missing)} selected videos: {missing[:5]}")
    picked["audio_path"] = picked["video_id"].map(lambda v: str(paths[v]))
    return picked


def write_manifest(chunk: pd.DataFrame, dest: Path) -> float:
    """Assign offsets within this batch and write it. Returns total runtime.

    Offsets restart at 0 for every batch: each becomes its own upload, so
    start_sec must describe position in THAT file.
    """
    rows, cursor = [], 0.0
    for seq, r in enumerate(chunk.itertuples(), start=1):
        rows.append({
            "seq": seq,
            "id": r.id,
            "video_id": r.video_id,
            "title": r.titles,
            "audio_path": r.audio_path,
            "duration_sec": round(r.duration_sec, 3),
            "start_sec": round(cursor, 3),
            "end_sec": round(cursor + r.duration_sec, 3),
        })
        cursor += r.duration_sec

    dest.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(dest, index=False, encoding="utf-8", lineterminator="\n")
    logging.info(f"wrote {dest}  --  {len(rows)} clips, {cursor/3600:.2f} h, "
                 f"longest {max(r['duration_sec'] for r in rows)/60:.1f} min, "
                 f"median {pd.Series([r['duration_sec'] for r in rows]).median()/60:.1f} min")
    return cursor


def main(source: Path, transcripts_raw: Path, audio_dir: Path, out_dir: Path,
         limit: int | None, max_clip_minutes: float | None,
         exclude: list[Path], batches: int, start_number: int,
         max_words: int, transcripts_dir: Path,
         max_words_per_minute: float | None) -> int:
    picked = select(source, transcripts_raw, audio_dir, exclude, max_words, transcripts_dir)
    logging.info(f"{len(picked)} videos selected for transcription")

    # Stable, meaningful order: by curation id, so the batch is reproducible and
    # a human scrubbing the uploaded video can predict what comes next.
    picked = picked.sort_values("id", key=lambda s: s.astype(int)).reset_index(drop=True)

    logging.info(f"probing durations for {len(picked)} clips")
    picked["duration_sec"] = [probe_duration(Path(p)) for p in picked["audio_path"]]

    # Trimming happens BEFORE offsets are assigned -- start_sec must describe
    # position in the file we actually build, not in the full candidate set.
    if max_clip_minutes:
        over = picked[picked["duration_sec"] > max_clip_minutes * 60]
        picked = picked[picked["duration_sec"] <= max_clip_minutes * 60]
        logging.info(f"dropped {len(over)} clips over {max_clip_minutes} min "
                     f"(longest {over['duration_sec'].max()/60:.1f} min)" if len(over) else
                     f"no clips over {max_clip_minutes} min")
    # Curation DENSITY, not volume. A 5-minute sketch with 60 curated words is
    # likelier to be partially transcribed than a 2-minute one with the same
    # count, and volume alone cannot tell them apart. Measured on the 45 videos
    # where the gain is observable, the low-density half had 24% of ASR
    # sentences uncovered by curation against 11% for the high-density half --
    # a weak predictor (r = -0.14) but the best one available before uploading.
    if max_words_per_minute:
        wpm = picked["words"] / (picked["duration_sec"] / 60)
        before = len(picked)
        picked = picked[wpm < max_words_per_minute]
        logging.info(f"kept {len(picked)} of {before} under {max_words_per_minute} "
                     f"curated words per minute")

    if limit:
        picked = picked.head(limit)
        logging.info(f"limited to the first {limit} by id")

    picked = picked.reset_index(drop=True)
    logging.info(f"{len(picked)} clips, {picked['duration_sec'].sum()/3600:.2f} h "
                 f"to split across {batches} batch(es)")

    if batches == 1:
        write_manifest(picked, out_dir / "manifest.csv")
        return 0

    chunks = split_balanced(picked, batches)
    if len(chunks) != batches:
        raise RuntimeError(f"asked for {batches} batches but split produced {len(chunks)}")

    total = 0.0
    for i, chunk in enumerate(chunks, start=start_number):
        total += write_manifest(chunk, out_dir / f"batch{i:02d}" / "manifest.csv")
    logging.info(f"{total/3600:.2f} h across {batches} batches "
                 f"(batch{start_number:02d}..batch{start_number + batches - 1:02d})")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", default=Path("kargin_eng.csv"), type=Path)
    p.add_argument("--transcripts-raw", default=Path("data/transcripts_raw"), type=Path)
    p.add_argument("--audio", default=Path("data/audio"), type=Path)
    p.add_argument("--out", default=Path("data/transcription_batch"), type=Path)
    p.add_argument("--limit", type=int, default=None,
                   help="keep only the first N clips by curation id")
    p.add_argument("--max-clip-minutes", type=float, default=None,
                   help="drop clips longer than this. A handful of 8-20 min outliers "
                        "dominate the total runtime; excluding them keeps a sample "
                        "representative (same median) instead of merely short.")
    p.add_argument("--exclude", nargs="*", default=[], type=Path,
                   help="manifests whose videos are already covered; their video_ids "
                        "are skipped so batches never overlap")
    p.add_argument("--batches", type=int, default=1,
                   help="split the selection into N manifests under <out>/batchNN/, "
                        "balanced by runtime rather than clip count (default 1)")
    p.add_argument("--start-number", type=int, default=1,
                   help="number the first batch directory from here (default 1)")
    p.add_argument("--max-words", type=int, default=0,
                   help="ceiling on curated dialogue. 0 = nothing curated (the first 87). "
                        "~50 reaches token curation; beyond that curation already runs "
                        "~95%% the length of ASR, so a transcript adds noise, not content.")
    p.add_argument("--transcripts", default=Path("data/transcripts"), type=Path,
                   help="videos already holding a good transcript here are skipped")
    p.add_argument("--max-words-per-minute", type=float, default=None,
                   help="keep only sketches curated more thinly than this, per minute of "
                        "runtime. Density beats raw word count as a predictor of what ASR "
                        "will add, though only weakly (r = -0.14).")
    a = p.parse_args()
    sys.exit(main(a.source, a.transcripts_raw, a.audio, a.out, a.limit,
                  a.max_clip_minutes, a.exclude, a.batches, a.start_number,
                  a.max_words, a.transcripts, a.max_words_per_minute))

