# Decisions

Significant design choices, newest first. Each records what was decided, why,
what was rejected, and what observation should trigger a revisit. Superseded
entries are never deleted — that we changed our mind, and why, is the point.

---

## #4 — Build all four uploads now, without waiting for pilot results

**Date:** 2026-08-02 · **Status:** active · **Reopens #3**

**Decision.** Build the remaining 57 videos into three more uploads
(`batch02`–`batch04`, 1.42 / 1.40 / 1.36 h) immediately, rather than waiting to
see whether the 30-clip pilot returns usable Armenian.

**Why.** Requested directly. Rendering is cheap and entirely local — roughly 30
minutes of CPU — and having all four ready means the uploads can be queued back
to back instead of serialised behind an ASR turnaround measured in hours.

**What this gives up.** #3's whole point was learning from one upload before
committing to the rest. If ASR comes back poor, the render time is wasted. That
cost is small and recoverable; the manifests and offsets stay valid regardless,
since only the audio content would be in question, never the split.

**Alternatives rejected.** Wait for the pilot (slower, and the only thing saved
is CPU time already sunk). Build all 87 as one upload (rejected in #3 and still
wrong — 5.89 h is a slow, all-or-nothing ASR job).

**What would change this.** If the pilot returns unusable text, stop before
uploading 02–04 and run the Whisper comparison in #1 instead. The renders can sit
on disk indefinitely; nothing forces them to be uploaded.

**Balancing note.** Batches are contiguous by curation id but balanced by
runtime, not clip count — durations are too uneven for equal counts (batch02 is
6 clips averaging ~14 min; batch04 is 26 averaging ~3 min).

---

## #3 — Pilot the batch with 30 clips before committing all 87

**Date:** 2026-08-02 · **Status:** revisited 2026-08-02, see #4

**Decision.** Build the first upload from a 30-clip sample (1.72 h) rather than
all 87 candidates (5.89 h).

**Why.** The full set runs 5.89 h. YouTube accepts that length on a verified
account, but ASR processing on a video that long is slow and, if it fails, tells
us nothing about *which* part failed. The sample costs one upload to learn
whether the whole approach produces usable Armenian text.

Selection is "drop clips over 6 minutes, then take the first 30 by curation id".
Six outliers (up to 19.6 min) dominate the total; excluding them yields a sample
whose median clip is 3.4 min — identical to the full 87's median, so the sample
is representative rather than merely short. Taking the 30 shortest would have
given 1.15 h but a 2.9 min ceiling.

**Alternatives rejected.** All 87 in one 5.89 h upload (slow feedback, all-or-
nothing). First 30 by id with no cap (2.81 h — over the 2 h target because of a
single 19.6 min clip). 30 shortest (1.15 h but skewed).

**What would change this.** If the pilot returns clean Armenian for most clips,
run the remaining 57 — splitting the >6 min outliers into their own batch.

---

## #2 — Split the returned transcript by manifest offsets, not on-screen markers

**Date:** 2026-08-02 · **Status:** active

**Decision.** Map captions back to source videos purely by timestamp against
`manifest.csv`'s `start_sec`/`end_sec`. The on-screen ID card is for human
verification only and is never parsed.

**Why.** YouTube captions are generated from audio. Nothing rendered on screen
reaches the caption track, so a visual ID cannot identify anything. Spoken
markers would reach it, but would be mis-transcribed and would corrupt the text
around each boundary. Durations are probed from the actual audio files, so
offsets are exact by construction.

Events are assigned by their **midpoint**, because ASR routinely emits a caption
window overlapping a boundary; midpoint puts it with the clip holding most of
it. Verified against synthetic captions: a deliberately straddling event landed
in the correct clip, and an event past the end was reported rather than silently
absorbed into the last clip.

**Alternatives rejected.** Spoken audio markers (corrupt neighbouring text).
On-screen text plus OCR (needless, offsets are already exact). Uploading each
clip separately would remove the split entirely, but `videos.insert` costs 1600
units against a 10,000/day quota — roughly 6 uploads/day. **Unverified; confirm
before scaling.**

**What would change this.** If the split reports many unassigned events, the
rendered audio has drifted from the manifest and the offsets are suspect.

---

## #1 — Get Armenian transcripts by re-uploading audio, not by running Whisper

**Date:** 2026-08-02 · **Status:** active

**Decision.** Concatenate the audio of videos lacking dialogue and upload it with
`defaultAudioLanguage` set explicitly to `hy`, then harvest YouTube's ASR.

**Why.** 618 of 702 videos have no usable transcript. YouTube's Armenian ASR is
good — the 84 `hy` tracks we hold are clean — but its language *auto-detection*
fails often on this audio: 92 videos came back Turkish, 48 English, 24 Russian,
20 Romanian. Wrong-language output is either empty (`[Müzik]` markers only) or
phonetic hallucination ("Chi Omega myrtana imports a culture jamming"). Setting
the language at upload removes the guess, which is the actual failure mode.

**Alternatives rejected.** Whisper large-v3 on the audio we already hold — no
upload, no quota, no waiting, and a GPU is available via the Colab CLI. Rejected
by the user in favour of shipping the upload route first. Note this was *not*
settled on measured quality: Armenian is low-resource for Whisper and it may be
better or worse than YouTube here. A three-way comparison was proposed (human
text vs YouTube `hy` vs Whisper, on the 84 videos that have both) and not run.

**What would change this.** If the 30-clip pilot returns poor Armenian, run that
bake-off before uploading the remaining 57 — the test set already exists.
