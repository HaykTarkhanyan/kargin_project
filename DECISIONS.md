# Decisions

Significant design choices, newest first. Each records what was decided, why,
what was rejected, and what observation should trigger a revisit. Superseded
entries are never deleted — that we changed our mind, and why, is the point.

---

## #16 — The site quiz is hand-written from the sketch dialogue, with stills cut from the videos

**Date:** 2026-09-11 · **Status:** active

**Decision.** The three placeholder trivia levels are replaced by 10-question
levels (four so far) in the style of the fan-made Google Forms quizzes captured under
`data/google_forms/`: a still from the sketch plus a question whose quoted line
is the funniest beat of the sketch, with wrong options that are jokes in their own
right ("who was in our house while I was away: Stalin, Vardan Mamikonyan,
Casanova, or neighbour Gegham"; "half of my goods is left, half is right: shoes,
gloves, earrings, or socks"; "who is the stinker: the driver, the auntie, the one
who said 'yes, I grabbed it too', or you"). Every answer, and most wrong options,
come from the sketch's own curated dialogue in `kargin_eng.csv`. The first draft
was straight trivia with literal distractors ("what colour was the solution");
the owner's review sent it back, and the rule above is what replaced it. Stills are cut by
`scripts/extract_quiz_stills.py` from `data/video/` at a hand-picked timestamp
listed in `data/quiz/stills.json`, 640 px wide, and committed under
`web/public/quiz/` with per-question file names. The runner gained three optional
fields: a question image, per-option images, and a sketch id that becomes a link
once the quiz is checked. The level/unlock/stars mechanic is unchanged.

**Why.** The old quiz asked how many sketches the archive has and how many hours
they run - facts about the website, not about Kargin, and nothing a fan would play
twice. The four forms show what fans actually make, and the fun is in the wrong
answers: the pig really was fed chocolate and used diapers as well, Vagharshak papi
really did offer ten, fifty and a thousand first. A template can pick a line; it
cannot pick a tempting distractor, so the questions are written by hand and the
Armenian is reviewed by the owner before it ships. Stills because three of the four
forms are picture quizzes. Per-question file names so the URL does not carry the
video id and give the answer away.

**Alternatives rejected.** Gemini-drafted questions (cents to run, but generic
humor and the same review effort; still the way to go if volume is ever wanted).
Template-only "which sketch is this still from" with the annotation titles as
options (the titles often contain the answer). YouTube thumbnails instead of cut
stills (no control over the frame, and the thumbnail is often the punchline). A
JSON question bank with a generator writing `quizzes.ts` (one level of ten
questions does not need a build step).

**What would change this.** More than about three levels, or a wish to rotate
questions - then the questions move under `data/quiz/` and `quizzes.ts` is
generated. Evidence that a sketch appearing twice in one level makes the
picture question trivial - then one sketch per level. Accounts or a leaderboard -
then answers stop living only in `localStorage`.

---

## #15 — Hearts are kept per device and every toggle is logged; no public count yet

**Date:** 2026-09-11 · **Status:** active

**Decision.** A heart button on every sketch card and on the watch page. The
visitor's own hearts live in `localStorage` (no account), each change is logged to
`events` as `heart` or `unheart` with the sketch and where it was tapped, and the
home page shows a "my hearts" filter once there is at least one. No public count
is shown anywhere. Cards changed from one big `<a>` to an `<article>` with a
stretched link, so the heart is a sibling of the link rather than a button inside it.

**Why.** There are no accounts and no Firebase web SDK on the site (#7), so the
device is the only place a heart can be remembered without a login. Logging reuses
the existing event pipeline: the rules only needed two more values in the `type`
allowlist. Both directions are logged because a ranking built from hearts alone
would credit a sketch for a tap somebody took straight back. The filter is there
because a heart you can never see again is a gesture into nothing. Counts are held
back because one device is one voice - a second phone, or clearing site data, is a
second vote - so small numbers would mean little and are cheap to inflate.

**Alternatives rejected.** A per-sketch counter the client increments (rules cannot
tell a tap from a script, so it is a public ballot box); Firebase anonymous auth
with a per-visitor document (pulls in the auth SDK that #7 avoided, and still has
the same one-device ceiling); a separate `hearts` collection (events already carry
sessionId, sketchId and source, and #14's reason for splitting - free text a human
reads - does not apply); keeping the card as one `<a>` and stopping the click
inside it (an interactive element inside `<a>` is invalid HTML).

**What would change this.** Accounts (hearts would move server-side and follow the
person). Enough heart events to rank on - then dedupe by sessionId, net out
unhearts, and decide whether a "most loved" list is worth showing. One sessionId
hearting hundreds of sketches would be the sign it is being gamed.

---

## #14 — Visitor reports go to their own Firestore collection, and the bot keeps no state

**Date:** 2026-09-11 · **Status:** active

**Decision.** "Couldn't find it? Tell us" on the site and in the bot, writing to a
new `feedback` collection — separate from `events`, create-only, unreadable by any
client, shape- and size-capped in `firestore.rules`. The send is awaited and its
failure is shown to the person who wrote it. In Telegram the prompt is sent with
`force_reply` and identified by its own first character, so the bot holds no
server-side "who is mid-report" state.

**Why.** Usage data (#13) showed people searching for lines the archive does not
have, and no way to say so. Reports are the only place a visitor types free text a
human will read, which makes them a different risk shape from telemetry: longer,
retained, and worth spam-capping separately, so they do not share `events`'
allowlist. Awaiting the write matters because unlike logging, somebody is waiting
to hear it landed — a silent failure would cost the report and the goodwill.
`force_reply` is what makes the bot work at all: it runs on Cloud Run scaled to
zero, so anything held in memory between two updates is gone.

**Alternatives rejected.** Reusing `events` (would loosen the telemetry contract
that is the site's whole abuse surface, and mixes 1 KB of prose into rows meant to
be counted); an in-memory conversation state in the bot (evaporates on scale-down,
which is the normal case, not an edge case); collecting the Telegram username as a
contact (the bot is pseudonymous by design — people who want a reply are asked to
put a contact in their own words instead); a mailto: link (no record, no
structure, and it exposes an address to scrapers).

**What would change this.** Spam. There is no rate limiting beyond the size caps —
if reports get abused, App Check on the web and a per-user cooldown in the bot are
the next steps, and both are additive. Also worth revisiting once anyone actually
triages these: there is no read path today, by design, so reading them means the
admin SDK (`scripts/non_essential/report_usage.py` is the natural place).

---

## #13 — Phrase search scores words by rarity, and misspellings by edit distance

**Date:** 2026-09-11 · **Status:** active

**Decision.** When the exact substring pass returns little and the query has two or
more words, match the words individually and score each sketch by the share of the
query's *information* it accounts for — inverse document frequency, so rare words
decide and filler does not. One word per phrase (the rarest, or one the archive
never says) is additionally expanded to near-spellings, ranked by Levenshtein
distance rather than Fuse's score. Highlighting follows the same rule, marking
each matched word so a card shows why it was returned.

**Why.** Usage data on 2026-09-11 showed 13 of ~56 distinct site queries returning
nothing, nearly all multi-word — people typing a line they remembered. Two causes,
both confirmed in code: exact matching is a contiguous substring test, so stored
punctuation breaks it; and the fuzzy fallback indexed single words but was handed
the whole phrase, so it could never match. Measured on the 702-sketch archive
(before → after):

| query | old | new |
|---|---|---|
| `լավ կառնեմ էտ` | 0 results, 1903 ms | 38, 187 ms |
| `պապա պտի ասես` | 0, 1897 ms | 28, 25 ms |
| `էտքանը որ անում եմ` | 0, 2584 ms | 15, 108 ms |
| `ասես էդ մեկը սովրել` | 0, 3543 ms | 16, 173 ms |
| `սարո` (misspelling of the role Սամո) | 507, 598 ms | 68, 61 ms |

Rarity weighting is load-bearing: counting words equally returned 538 of 702
sketches for `պապա պտի ասես`, matched entirely on "պտի" and "եմ".

**Alternatives rejected.** Plain AND-of-words (a wrong remembered word zeroes the
query; and stopwords satisfy it); a fixed count of words to match (no threshold
separates "matched two filler words" from "matched the one word that mattered");
keeping Fuse for near-spellings — measured at 481-1096 ms per lookup against
85-130 ms for a length-bucketed edit-distance scan, and far less precise: it
offered 195 candidates for "կառնեմ" where 8 are within one edit, and its Bitap
score saturates on short words, giving "սամո" and 457 unrelated words an identical
0.25. Fuse is no longer imported, and `fuse.js` was removed from `package.json`
on 2026-09-11 — the archive's only search dependency is now its own code.

**What would change this.** A corpus large enough that scanning every sketch per
word costs too much (it is ~25-190 ms at 702, and grows linearly), or a real
index/embedding search if the bot ever gains a server. The thresholds are
fractions of `log(corpus size)`, so they do not need retuning as the archive grows.

---

## #12 — Sketch similarity via gemini-embedding-2 over the English detailed summaries

**Date:** 2026-09-08 · **Status:** active

**Decision.** Embed `summary_detailed_en` for all 702 sketches with
`gemini-embedding-2` on Vertex (3072-dim, `task_type=SEMANTIC_SIMILARITY`),
L2-normalize, and keep the full vectors and the full 702×702 cosine matrix
locally as the artifacts of record; ship only each sketch's top-10 neighbour
ids and scores. Script: `scripts/embed_annotations.py`. One API request per
document — see below.

**Why.** User picked the model from a presented shortlist. It was already
enabled on the project (same credits, same ADC, same SDK as the annotation
sweep — no new dependency), is Matryoshka-truncatable to 768 dims if vectors
ever need shipping, and is natively multimodal, so the 702 contact sheets and
audio files could later share one vector space. Whole corpus cost **$0.027** in
27.7s. Validated three ways: (1) all **23/23** strict duplicate pairs found
independently by audio fingerprinting rank #1 by cosine (mean 0.896 vs 0.553
background) — the embedding never saw the audio; (2) top-1 neighbours share a
topic 93.9% of the time vs 43.9% for random pairs (Jaccard 0.456 vs 0.121,
3.8×); (3) visual `location_fine` word-overlap is 6.6× random. Only 5
non-duplicate pairs exceed cosine 0.85, so the top end is sparse rather than
collapsed.

**Alternatives rejected.** Self-hosted open-weight embedders (Qwen3-Embedding,
BGE) — free and comparable at this corpus size, but add torch plus a model
download to a repo that has neither; Armenian-specialised models
(`armenian-text-embeddings-2`, the ate3 soup) — the documents being embedded
are English, so Armenian cross-lingual strength is not the relevant axis;
shipping full vectors (8.6 MB float32) — the site's data bundle was
deliberately cut to 1.6 MB, and precomputed neighbours cost 182 KB.

**Batching trap (load-bearing).** `embed_content(contents=[a,b,c])` returns
**one** embedding on Vertex, silently dropping the rest — verified at batch
sizes 2, 4 and 8. Batching would have produced 44 vectors for 702 documents,
misaligned against their video ids, with no error anywhere. The script sends one
document per request, parallelises with `--workers`, and asserts the returned
count on every call.

**Boilerplate-stripping tested and rejected (2026-09-08).** The obvious next
experiment — strip the formulaic "The sketch takes place in…" opener that 467 of
702 summaries share — was run for $0.027 into side-by-side `*__stripped`
artifacts. It lowered the similarity floor exactly as predicted (0.553 → 0.458)
and improved relative separation (2.29 → 2.63 sd), but neighbour *quality* got
slightly worse: at matched percentiles `full` has higher topic agreement in every
band (top 0.1%: 0.494 vs 0.468; top 1%: 0.321 vs 0.297). The opener carries the
setting and acts as an alignment anchor rather than noise. `full` stays the
shipping variant; both artifact sets are kept and `--variant` selects. Full
numbers in `LEARNINGS.md`.

**Ship neighbours by score, not by rank.** Good matches are scarce: only 53 of
702 sketches have any neighbour above cosine 0.85, 292 above 0.75, and 256
sketches have no neighbour above 0.72 at all. Quality tracks the score, not the
rank (sampled pairs are excellent ≥0.80, mixed 0.70–0.75, noise below 0.70 —
"The Boss and the Seductive Secretary" pairs with "Nazi Interrogation" at 0.669).
A fixed top-10 would show most sketches eight or nine unrelated matches, so the
surface should threshold around 0.75 and display fewer, often none. The full
matrix is on disk, so the cutoff is a one-line change with no re-embedding.

**Known limitation — provenance clustering.** The 12 Claude-written summaries
cluster with each other more than content alone explains: mean pairwise cosine
0.647 vs 0.603 for a content-matched control of Gemini rows with the same dark
profile (p=0.004), against 0.553 uniform-random. About half the gap is genuine
shared content (they are the 12 sketches the filter blocked, all dark) and half
is writing style. It affects 12 rows of 702, 8 of the 12 still take a Gemini row
as top-1, and the pairings it does produce are mostly correct — accepted rather
than fixed.

**What would change this.** Query-time semantic search (needs a server; the
static site has none, the bot does); a future re-annotation pass that rewrites
the 12 Claude rows in the Gemini register, which would remove the style artifact.

---

## #10 — Sketch dialogue is a bounded preview on cards, never a scroll box

**Date:** 2026-09-08 · **Status:** active

**Decision.** Card dialogue renders at most 5 lines inside a 128px `overflow-hidden`
box (faded at the cut, remainder counted as "+N տող"). No nested scrollers anywhere
in the browse or watch UI: the watch-page transcript became a native `<details>`
instead of a 288px scroll area.

**Why.** On touch, a drag inside an `overflow-y-auto` box scrolls that box, not the
page. The home page shipped 48 of them — one per card, 144px tall holding up to
5,271px of transcript — so on a phone most swipes landed in a trap. Measured on
the live site 2026-09-08: 48 trap elements on `/`, 1 on a watch page. After: 0 on
every route. This is the bug Hayk reported as "scrolling scrolls the description
instead of the page". Card heights went from 478–2,536px to 478–550px.

**Alternatives rejected.** `touch-action`/`overscroll-behavior` tuning (arbitrates
the gesture, keeps a 144px window onto 36 screenfuls — nobody reads a transcript
that way); keeping scroll on desktop only (two behaviours to maintain, and a wheel
over a card traps there too); CSS `line-clamp` (unreliable across multiple block
children — the pixel cap is deterministic).

**What would change this.** Anyone wanting full dialogue in the grid — it belongs
on the detail page, which the card links to. If cards ever need to be read rather
than scanned, the cap is one constant (`PREVIEW_LINES`).

---

## #11 — Actor pages cap at 48 cards and hand off to search

**Date:** 2026-09-08 · **Status:** active

**Decision.** `/actor/[name]` renders its first 48 sketches server-side and links to
`/?actor=<name>` for the rest, rather than every sketch the actor appears in.

**Why.** Hayko is in 532 sketches: that page shipped 3.25 MB of HTML, 11,129 DOM
nodes and stood 486 phone-screens tall — a long cellular download for a page nobody
scrolls to the end of. Capped it is 295 KB / 1,128 nodes / 40 screens, a 91% cut.
Search already filters by actor, sorts, and pages.

**Alternatives rejected.** A client-side "load more" like the home grid — tried and
measured: making `SketchGrid` a client component serialised all 532 sketch objects
into the RSC payload, so the page only fell to 2.2 MB (2.1 MB of it inline
`<script>`). Passing a full array across a `"use client"` boundary costs the whole
array whether or not it is rendered.

**What would change this.** Actor pages needing to be crawlable in full, or the
grid gaining server-side pagination via route segments.

---

## #9 — Text annotations: gemini-3-flash-preview, thinking off, schema v2 with visual input

**Date:** 2026-09-07 · **Status:** active (sweep completed 2026-09-07: 690/702 by
Gemini for $2.00; the 12 rows Google's content filter refused were annotated by
Claude Opus 5 in-session from identical input and carry `model: claude-opus-5`
plus a `provenance_note`. All 702 validate against the schema.)

**Decision.** Extract per-sketch annotation columns (titles hy+en, short + detailed
English summaries, keyword triplets hy/en/translit, verbatim catchphrases, topics
from a fixed 24-value vocabulary, humor types) with `gemini-3-flash-preview` on
Vertex AI, `thinking_budget=0`, structured output via `response_schema`, input =
curated text + YouTube transcript + visual annotation. Script:
`scripts/extract_text_annotations.py` (idempotent: atomic writes, skip-existing,
corrupt-file regeneration; parallel via `--workers`; per-call cost ledger
`data/gemini_spend_ledger.jsonl`).

**Why.** ArmBench-LLM (live leaderboard, checked 2026-09-07) ranks Gemini 3 Flash
#1 for Armenian (0.635), beating every Pro model — including Gemini's own
(3-pro 0.595, 3.1-pro 0.522). A 10-row pilot vs `gemini-3.8-flash` (unbenchmarked
on Armenian) showed no quality edge for 3.8 at higher cost. Disabling thinking cut
per-row cost ~55% ($0.0044 → $0.0020 v1) with zero observed quality loss across 10
rows (sometimes better scene coverage). Adding visual annotations (schema v2)
resolved premise-level errors: exposed seq 273 as a compilation, fixed seq 66's
two-scene coverage. Claude comparison (Sonnet/Opus subagents + Fable inline, 2
rows): Opus/Fable summaries were best (punchline capture), but the gap is confined
to summary depth — search fields were equivalent — and Claude costs ~$65 (Opus
API) or a large session-quota bite vs ≈$2.20 total on GCP credits. Full pilot
evidence: `data/text_annotations_pilot*/report.html`; total pilot spend $0.174.

**Alternatives rejected.** `gemini-3.8-flash` (no Armenian benchmark data, +25%
cost, no observed quality gain); Gemini Pro models (score *worse* on Armenian, cost
more); Claude models for the bulk sweep (quality edge real but narrow; cost/quota
profile wrong for 702 rows — reserved as an option for a hand-picked subset);
model self-reported `confidence` field (30/32 pilot outputs said "high" — dropped
in favor of code-side input profile); free-form tags (fragment into one-off
values — fixed vocabulary enforced by enum instead).

**Topic vocabulary (24).** Built from data, not intuition: aggregated
`location_fine`, `character_types` and `visual_synopsis` across all 702 visual
annotations plus the curated `location` column. Evidence-driven additions on
2026-09-07: `restaurant_cafe` (19 restaurant + 5 cafe locations, 11 waiter/8
bartender roles), `crime` (14 gangster), `wedding_funeral` (23 — weddings,
banquet halls, funeral processions, 4 hearses, wakes), `party_guests` (~40 —
birthdays, house parties, hosting), `leisure_outing` (~30 — zoo, museum,
theater, beach, fishing); `media_tv` renamed `media_showbiz` (53 hits span
stage/singers/reporters, not just TV). Validated on 13 rows: `other` fell from
5/10 rows to 1/10, and the three new values were each picked on rows known to
contain them. Rejected for thin evidence: `repair_construction` (23, `work`
covers it), `games_gambling` (14), emigration/abroad (8), barber/salon (2).
Humor-type vocabulary left at 9 — `parody` and `innuendo` were proposed and
declined by the user.

**What would change this.** ArmBench adding 3.5–3.8 Flash results that show a
meaningfully stronger model; visible quality gaps in the swept summaries (a
Claude re-pass on affected rows is the fallback); Gemini 3 Flash preview being
deprecated (move to the then-current Flash after a 10-row re-pilot).

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
