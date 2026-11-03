"""Throwaway (Phase 0.1): build query clips with known right answers for the engine probe.

Positives from data/duplicates.csv (the 2026-08-01 run) plus planted clips cut from
the middle of 20 archive sketches. Robustness variants (speed-ups) and negatives
(reversed speech, noise). Writes clips + groundtruth.csv under <out>/.
Runtime: ~1-2 min (ffmpeg, one process).
"""
import csv
import random
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(sys.argv[1])
OUT = Path(sys.argv[2])
CLIPS = OUT / "clips"
CLIPS.mkdir(parents=True, exist_ok=True)
AUDIO_RE = re.compile(r"^(\d{3})_.*?([A-Za-z0-9_-]{11})\.[^.]+$")

paths = {}
for p in (ROOT / "data" / "audio").iterdir():
    m = AUDIO_RE.match(p.name)
    if m:
        paths[m.group(2)] = p
meta = pd.read_csv(ROOT / "data" / "youtube_metadata.csv")
dur = dict(zip(meta.video_id, meta.duration_sec))
print(f"archive audio files: {len(paths)}")


def ff(args):
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", *args], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode(errors="replace")[:400])


rows = []
# 1. Known pairs. Query = the first 60 s of one member; the other member must be found.
d = pd.read_csv(ROOT / "data" / "duplicates.csv")
for _, r in d[d.verdict.isin(["duplicate", "contains"])].iterrows():
    if r.verdict == "contains":
        q, ref = r.included_sketch, r.compilation
    else:
        q, ref = r.video_id_b, r.video_id_a
    out = CLIPS / f"pair_{r.verdict}_{q}.mp3"
    if not out.exists():
        ff(["-t", "60", "-i", str(paths[q]), "-ac", "1", "-b:a", "64k", str(out)])
    rows.append(dict(clip=out.name, kind=f"known_{r.verdict}", source=q, expect_ref=ref,
                     expect_offset="", note="first 60 s of the query member; self-match also expected"))

# 2. Planted clips from the middle of 20 sketches (seed 509), and their variants.
random.seed(509)
pool = sorted(v for v in paths if (dur.get(v) or 0) >= 150)
picks = random.sample(pool, 20)
noise = OUT / "pink20.wav"
if not noise.exists():
    ff(["-f", "lavfi", "-i", "anoisesrc=color=pink:duration=20:sample_rate=22050:amplitude=0.3", str(noise)])
for v in picks:
    start = round(dur[v] / 2 - 30, 1)
    base = CLIPS / f"mid_{v}.mp3"
    if not base.exists():
        ff(["-ss", str(start), "-t", "60", "-i", str(paths[v]), "-ac", "1", "-b:a", "64k", str(base)])
    variants = {
        "mid_plain": (base, start, "60 s from the middle, mp3 64k"),
    }
    intro = CLIPS / f"intro_{v}.mp3"
    if not intro.exists():
        ff(["-i", str(noise), "-i", str(base), "-filter_complex",
            "[0:a]aresample=44100,aformat=channel_layouts=mono[n];[1:a]aresample=44100,aformat=channel_layouts=mono[b];[n][b]concat=n=2:v=0:a=1",
            "-b:a", "64k", str(intro)])
    variants["mid_intro20"] = (intro, start - 20, "20 s pink-noise intro, then the same clip (ref offset = clip start - 20)")
    pitch = CLIPS / f"speed4p_{v}.mp3"
    if not pitch.exists():
        ff(["-i", str(base), "-af", "aresample=44100,asetrate=44100*1.04,aresample=44100", "-b:a", "64k", str(pitch)])
    variants["speed4_pitch"] = (pitch, start, "sped up 4% with pitch (asetrate), like a tape run fast")
    tempo = CLIPS / f"speed4tempo_{v}.mp3"
    if not tempo.exists():
        ff(["-i", str(base), "-af", "atempo=1.04", "-b:a", "64k", str(tempo)])
    variants["speed4_tempo"] = (tempo, start, "sped up 4%, pitch kept (atempo)")
    rev = CLIPS / f"reversed_{v}.mp3"
    if not rev.exists():
        ff(["-i", str(base), "-af", "areverse", "-b:a", "64k", str(rev)])
    for kind, (p, off, note) in variants.items():
        rows.append(dict(clip=p.name, kind=kind, source=v, expect_ref=v, expect_offset=off, note=note))
    rows.append(dict(clip=rev.name, kind="neg_reversed", source=v, expect_ref="", expect_offset="",
                     note="reversed speech: same spectrum statistics, must match nothing"))

noise60 = CLIPS / "neg_noise60.mp3"
if not noise60.exists():
    ff(["-f", "lavfi", "-i", "anoisesrc=color=pink:duration=60:sample_rate=22050:amplitude=0.3", "-b:a", "64k", str(noise60)])
rows.append(dict(clip=noise60.name, kind="neg_noise", source="", expect_ref="", expect_offset="", note="pure pink noise"))

with open(OUT / "groundtruth.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(f"{len(rows)} ground-truth queries -> {OUT / 'groundtruth.csv'}")
print(pd.Series([r["kind"] for r in rows]).value_counts().to_string())
