# Decisions

Significant design choices, newest first. Each records what was decided, why,
what was rejected, and what observation should trigger a revisit. Superseded
entries are never deleted — that we changed our mind, and why, is the point.

---

## #8 — Telegram bot in Node/TS importing the website's search, on Cloud Run

**Date:** 2026-09-07 · **Status:** active

**Decision.** The Telegram bot (`bot/`) is Node/TypeScript with grammY and
imports `web/lib/search.ts` (plus translit/normalize/format/types) directly by
relative path — one search implementation for both surfaces. Hosting target is
Cloud Run in webhook mode (scale to zero); long polling for local dev. Data is
the same `sketches.json` artifact the site bundles, baked into the image.
Usage events go to the same Firestore `events` collection (source `bot`,
sha256-hashed user ids).

**Why.** The old project's central defect was two surfaces with duplicated
fuzzywuzzy search that drifted (see project CLAUDE.md). Importing the web lib
makes drift structurally impossible — the bot's tests assert an Armenian query
and its Latin transliteration hit the same sketches via the identical code
path. grammY chosen over Telegraf as the most actively maintained TS-first
framework (verified 2026-09-07). User picked all four options 2026-09-07:
runtime, hosting, v1 features (search + inline + /random), result UX
(youtu.be link that plays in-chat + site button).

**Alternatives rejected.** Python bot (re-implements search, guaranteed
drift); reviving `old/telegram_bot.py` (built on the duplicated-search
pattern); Firestore as the bot's data source (702 reads per cold query for
data that fits in memory).

**What would change this.** If the site ever drops the static-bundle data
model, the bot's fs-read of `sketches.json` moves with it. If bot traffic ever
exceeds polling comfort locally, webhook mode is already the deploy default.

---

## #7 — Log events over Firestore REST + fetch(keepalive), not the web SDK

**Date:** 2026-09-06 · **Status:** active

**Decision.** The site's usage logging writes to Firestore's REST
`documents:commit` endpoint with `fetch(keepalive)`; the Firebase web SDK is not
loaded on the logging path. Fields are clamped client-side; security rules
enforce the same contract as a backstop.

**Why.** Independent design review showed that lazy-loading the SDK at flush
time loses *entire short sessions* (the SDK chunk can't fetch + init + write
while the tab is being killed), and the SDK gives no keepalive guarantee on
unload. Rules apply to every access path including raw HTTPS, so REST loses no
security. `fetch(keepalive)` is what the current `lib/log.ts` fallback already
uses — delivery semantics are preserved exactly.

**Alternatives rejected.** Full web SDK (heavy, unload-unreliable);
`firebase/firestore/lite` (smaller, still no keepalive); keeping the Cloudflare
Worker (a server we no longer need).

**What would change this.** If the site later loads the Firestore SDK anyway
for interactive features, the logging path can piggyback on it — reopen then.

---

## #6 — Blaze plan with a ~$10 budget alert, not Spark

**Date:** 2026-09-06 · **Status:** active

**Decision.** The Firebase project runs on the Blaze (pay-as-you-go) plan with
a ~$10/month budget alert, even though expected steady-state cost is ≈ $0.

**Why.** Spark's Hosting cap is 10 GB transfer/month and the failure mode is
the site being *disabled* until next month. The built export is ~103 MB and one
widely shared link could plausibly hit the cap. Blaze keeps every free
allowance and converts the outage into a small bill; the user approved "a few
$/month". It also unblocks the Firestore→BigQuery extension for analytics later.

**Alternatives rejected.** Spark (site-goes-dark failure mode); pre-emptive
paid capacity (nothing to buy — Blaze is usage-priced).

**What would change this.** A real bill above a few $/month → investigate
traffic, consider tighter caching or moving bulk assets.

---

## #5 — Migrate to Firebase: static Hosting + Firestore, no SSR

**Date:** 2026-09-06 · **Status:** active

**Decision.** Move hosting from GitHub Pages to classic Firebase Hosting,
keeping the Next.js static export exactly as is. Firestore holds anonymous
usage events (replacing the Cloudflare Worker + Neon Postgres) and a mirror of
the sketch catalog for future dynamic features. `kargin_eng.csv` + annotations
in git remain the source of truth; a CI script syncs them into Firestore after
each successful deploy. Search keeps the statically bundled JSON.

**Why.** The user wants the site on GCP with Firestore as the foundation for
dynamic features. Since data edits are git commits, every change already
triggers a CI rebuild — SSR's "fresh data without rebuild" buys nothing here.
Serving the search index from Firestore would cost ~702 doc reads per visitor
(free tier exhausted at ~70 visitors/day) and be slower than CDN-cached static
chunks. Full design: `docs/superpowers/specs/2026-09-06-firebase-migration-design.md`.

**Alternatives rejected.** Firebase App Hosting SSR (big code migration, per-view
compute + reads, benefit void given the git workflow); hybrid static-plus-client-
rehydrate (two data paths for the same content, permanent staleness trap);
staying on Pages + adding Firestore only (rejected by the user — the point is
consolidating on GCP).

**What would change this.** Data starts being edited outside git (admin UI,
crowdsourcing) → revisit SSR/App Hosting. Sustained traffic past ~70k
reads/day on dynamic features → revisit the read model.

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

**Outcome (2026-08-02, same day).** All four were uploaded and returned captions.
**87 videos, 111,266 Armenian characters; 80 of 87 carry more than 500.** Only 3
are weak, and one of those is a 40-second clip. The risk this entry took on did
not materialise, and building ahead saved a full ASR turnaround per batch.

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
