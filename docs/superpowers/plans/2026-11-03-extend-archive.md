# Extending the archive beyond the 702 sketches

Plan, written 2026-11-03, revised the same day to cover compilations, then reviewed
against the code (findings and what changed: section 15). **Nothing here has been
run yet.** This file is the full record: every finding, number and
open decision lives here, not in the chat. Answer decisions by their ID (`Q5: b`).

Inputs: the channel scout (`data/channel_scout/`, DECISIONS #18), a read of every
pipeline script's docstring and of the build, review and annotation code,
_learnings/, DECISIONS.md, HANDOFF.md, and the measurements quoted below.

Contents:

1. [Summary](#1-summary)
2. [What the code and data force on us](#2-what-the-code-and-data-force-on-us)
3. [Decisions](#3-decisions)
4. [The kinds of video involved](#4-the-kinds-of-video-involved)
5. [Phase 0 - an engine that finds audio anywhere](#5-phase-0---an-engine-that-finds-audio-anywhere)
6. [Phase A - standalone candidates](#6-phase-a---standalone-candidates)
7. [Phase M - mapping compilations, episodes and tapes](#7-phase-m---mapping-compilations-episodes-and-tapes)
8. [Phase B - adding whole-video sketches](#8-phase-b---adding-whole-video-sketches)
9. [Phase S - compilations on the site](#9-phase-s---compilations-on-the-site)
10. [Phase C - sketches that exist only inside a longer video](#10-phase-c---sketches-that-exist-only-inside-a-longer-video)
11. [Money, Claude usage, time, disk](#11-money-claude-usage-time-disk)
12. [Done checklists](#12-done-checklists)
13. [Gotchas to carry through](#13-gotchas-to-carry-through)
14. [Sources](#14-sources)
15. [Review log](#15-review-log)
16. [Progress log](#16-progress-log)

---

## 1. Summary

All 702 archive sketches come from KarginTV. The scout found 232 channels and
9,813 videos outside the archive. Three kinds of thing are in there:

- **Standalone sketches**: one sketch per video, 1-15 min. These drop into the
  current data model unchanged.
- **Multi-sketch videos**: fan compilations, full TV episodes and the hour-long
  Kargin Kaset tapes. About 307 videos and 168 hours. They are mostly sketches we
  already have, but some of their content may exist nowhere else.
- **Fragments**: shorts and clips cut from one sketch. 6,110 shorts, skipped by default.

The archive itself already holds about 8 compilations (six of them 566-1,177 s
long), and the audio check mapped only 2 of them, because it looks at the first 60 s
only.

The order of work:

1. **Phase 0** builds one audio engine that can find any piece of audio anywhere
   inside the archive or inside a long video.
2. **Phase A** uses it to sort the standalone candidates into "have it" and "new".
3. **Phase M** uses it to map every compilation, episode and tape onto the archive.
   What's left over are the unknown parts; if a standalone upload of an unknown part
   exists anywhere, that upload joins the archive.
4. **Phase B** adds the approved standalone sketches with the existing pipeline.
5. **Phase S** marks compilations on the site and links them to the sketches they contain.
6. **Phase C**, sketches that exist only inside a longer video, needs a new ID
   scheme. It is in scope (Q5): its spec, including a stable archive id (Q16), is
   written while Phase M runs.

Scope (Q5): Kargin Haghordum, Kargin Multer and Kargin Kaset. Kargin Sketch Show is out.
7. **B20** then watches every archive video monthly for uploads that died, because
   fan copies are likelier to vanish than KarginTV's.

## 2. What the code and data force on us

1. **A sketch is a YouTube video.** `id`, `videoId`, the URL, the thumbnail and every
   lookup (songs, transcripts, visual, neighbours, the Firestore doc, hearts, events)
   are keyed by the 11-char video id (`scripts/kargin_build/assemble.py:41-51`). A
   sketch at 15:39 inside a 30-minute episode would share an id with every other
   sketch in it. Whole-video sketches therefore need no code change, and segments
   need Phase C.
2. **`id` and the file prefix are the row position in `data/youtube_metadata.csv`.**
   Files are `NNN_<title>_<video_id>.<ext>` under `data/audio`, `data/video`,
   `data/contact_sheets` and `data/transcripts`; annotations are
   `NNN_<video_id>.json`. New rows must be appended, never inserted, reordered or
   removed once their files exist. `download_audio.py`, `download_video.py` and
   `fetch_transcripts.py` recompute the number by enumerating the metadata rows after
   dropping those whose `availability` is not public. A video that is deleted or made
   private comes back from the API as an error row with an EMPTY `availability`,
   which the filter treats as public (`fillna("public")`), so it keeps its slot. A
   video that comes back as **unlisted** is dropped, and every later number shifts.
   `--refresh` also overwrites a dead video's good metadata with that empty error
   row. `scripts/audit_audio.py` check 6 catches a shift, so it gates every fetch.
3. **999 is a hard ceiling today.** Four scripts parse `^(\d{3})_`
   (`audit_audio.py:45`, `detect_duplicates.py:74`, `fingerprint_audio.py:56`,
   `recognize_songs.py:88`). That leaves room for 297 more; past that, widen the
   regex to `\d{3,}` first.
4. **Disk: 16 GB free of 476 GB (97% full), measured 2026-11-03.** One archived sketch
   costs about 11.5 MB (audio 2.3, video 8.7, sheet 0.5; measured from `data/` at 1.6
   GB, 6.1 GB and 344 MB for 702). Screening a standalone candidate costs about 0.7
   MB. The multi-sketch pool needs 3.5 GB of audio at 48 kbps, 8.9 GB at the
   archive's bitrate.
5. **Only audio can say "same recording".** Titles are templates, durations collide by
   chance (162 groups), and same-title rows have turned out to be different sketches
   (_learnings/ 2026-08-01). The current check is a fingerprint shortlist plus
   sample-level cross-correlation, which separates 0.86-0.99 (same) from 0.010-0.015
   (unrelated). **But it compares the first 60 s of two files only.** It misses a
   fan cut with a long intro and anything that isn't at the start, which is
   everything in a compilation.
6. **The visual pass is blind and never names actors**
   (`.claude/skills/annotate-sheets/SKILL.md`). Who is in a sketch comes from text
   cues (titles, descriptions, dialogue) or from a person (Q11).
7. **`duplicate_of` has no safe writer.** `annotate_kargin_csv.py` rewrites the CSV
   header order (HANDOFF warns not to run it), and the review UI refuses the field.
8. **Compilations are already in the archive.** The visual pass flagged 8:
   `Fyc5VWnAMog` (1,177 s), `3UZOwmPovQ4` (1,068), `mrIUW3fCUUo` (1,035),
   `lO4fAllxmwc` (960), `E0apclx3wqU` (877), `L3CiQABljX8` (566), plus
   `VFajwBRJxc4` and `aOZ3vbc1iFA`. `data/duplicates.csv` maps only `E0apclx3wqU`
   (contains `R6VbgKcNBYY`, `kIc8JOhTGbE`) and `3UZOwmPovQ4` (contains
   `0iKAm_aZ7Og`, `kKDydl5jRAY` at a 3.8 s lag). On the site today a compilation
   shows up as one "sketch": it counts toward the total, lands in `/random`, repeats
   its components in search, and its embedding is a mixture that pollutes "similar".
9. **The site hardcodes the count.**
   - `web/app/layout.tsx:17` (page description "Որոնիր 702 Կարգին սքեթչ")
   - `web/app/stats/page.tsx:12` (a literal "702" card, plus "10 ամիս")
   - `web/app/about/page.tsx:90,115` (history of how the first 702 were processed)
10. **The player is a YouTube iframe** (`web/components/WatchView.tsx:20`,
    `youtube.com/embed/<videoId>`). A video with embedding turned off, blocked in the
    viewer's country, or age-restricted plays nothing on our page. All 702 current
    videos are embeddable (`data/youtube_metadata.csv`), so this has never come up.
    Fan uploads are not guaranteed to be.
11. **Fan uploads die more often than KarginTV's**, through takedowns and deleted
    channels. This is plausible but not measured yet. A dead upload means a dead
    player on our page, and because the sketch id IS the video id, switching the
    sketch to another copy changes its URL and orphans hearts and shared links.
    Nothing checks for dead videos today. Our local copy survives, but the site
    never shows it.
12. **The whole archive ships in the home page's JavaScript.** `web/lib/data.ts:2`
    imports `sketches.json`, 2.76 MB for 702 sketches (about 3.9 KB each). 114 more
    is about +0.45 MB, 300 more about +1.2 MB, before compression.

## 3. Decisions

All answered 2026-11-03 in an interview. The plan below follows these answers. Where
an answer overrode my recommendation, that is noted, because why a recommendation
lost is worth keeping.

| ID | Decision | Answer | What it changes in this plan |
|---|---|---|---|
| Q4 | Commit `data/channel_scout/videos.json` (9.2 MB)? | **Commit it.** Overrode my "keep it ignored" | Ignore line removed, file committed |
| Q5 | Scope | **Kargin Haghordum, Kargin Multer and Kargin Kaset. Not Kargin Sketch Show.** Sketches that exist only inside a longer video are in scope: Phase C is a firm yes, not conditional on Phase M's count | The 100 Sketch Show uploads leave A2; Phase M includes the Kaset tapes; the Phase C spec is written while Phase M runs |
| Q6 | Match the fan uploads against the 702 | Folded into Phase 0 + A | - |
| Q7 | `series` column | **Yes** | Values `haghordum`, `multer`, `kaset`. KARGIN SHOW episodes carry Haghordum sketches, so their sketches are `haghordum`. Added in B1, shipped in B13/B14 |
| Q8 | Which upload becomes the archive's copy | **The proposed rule.** Hard requirements first: public, embeddable, not blocked in Armenia or Germany, not age-restricted. Then highest resolution; then clean audio with no crop, mirror or watermark; then the channel likeliest to keep it up; then earliest upload. The other copies are kept as alternates | A5 |
| Q9 | Free disk space first? | **Work within the 16 GB.** Overrode my "hunt first" | Each phase's screening audio is deleted, by exact path and with your OK, once its results are saved and before the next phase downloads (A3, M3). Phase M audio goes in priority batches |
| Q10 | Transcripts for new sketches | **Batch re-upload; you upload the video** | B5 |
| Q11 | Actors on new sketches | **Text cues only; tag the rest later.** Overrode my "tag before publishing". Face-based identification is off the table (note below) | New pre-fill step from titles, descriptions and transcripts (B11). Untagged sketches ship, and they're missing from actor pages and the actor filter until tagged. Measured: only 10% of standalone candidates name the Hayko+Mko pair in the title, 15% name any main actor in the title or description; transcripts add more |
| Q12 | Review of this plan | Done inline, section 15 | - |
| Q13 | Engine for finding audio anywhere | **Probe audfprint first, fall back to extending our own fingerprint** | Phase 0 |
| Q14 | The archive's own ~8 compilations | **Keep them and mark them** | Phase S |
| Q15 | New compilations from fan channels | **Mine them only, never add them** | Phase M |
| Q16 | When an archive upload dies | **A stable archive id, designed in the Phase C spec**, covering both segments and swapping a dead upload for an alternate. Until it ships, a dead video's page says the video is gone and links the alternate | Phase C spec, B20 |
| Q17 | Show the uploading channel | **Yes** | B13: `uploader` shipped, shown on non-KarginTV pages; stats that mix official and fan view counts are labelled |
| Q18 | Curated display titles | **Decide after the triage** | A6 notes the bad titles; decide when that list exists |
| Q19 | Harden the numbering | **Yes, before anything else in Phase B** | B0: the three downloaders take the number from the `id` column |

**Note on Q11, recorded because it came up:** putting a name to a real person from
their face is something I don't do, in any context. Here the people are well-known
comedians and the goal is harmless, but the capability is the same whether the face
is Hayko in a sketch or a stranger in a photo, so the line holds everywhere. It also
matches the project's own rule in `.claude/skills/annotate-sheets/SKILL.md` ("Do not
identify real actors by name from faces"). Names from titles, descriptions, dialogue
and your own lists are all fine.

## 4. The kinds of video involved

Measured on `data/channel_scout/videos.csv` (other channels) and the archive.

| Kind | Where | Count | What we do |
|---|---|---|---|
| Standalone sketch, 1-15 min | other channels | 2,028 sketch-length videos, not Serial. That includes the 67 compilation-titled and 44 long rows below, which A1 separates out, so roughly 1,900 true standalone candidates | Phase A, then Phase B |
| Standalone sketch on KarginTV, not in the archive | KarginTV | 6 Haghordum titles (175, 176, 177, 194, 195, Bufet) + 8 Multer in scope; the 100 Sketch Show uploads are out (Q5). **Corrected 2026-11-03 by the audio match: "175" is the archive's sketch 125 and "Bufet" is sketch 198 (same durations), so 4 Haghordum sketches are missing, not 6** | Phase A with matching (KarginTV re-uploads its own sketches: all 23 duplicate pairs in the archive are KarginTV vs KarginTV), then Phase B |
| Compilation already in the archive | KarginTV | ~8; six are 566-1,177 s, the other two (`VFajwBRJxc4`, `aOZ3vbc1iFA`) flagged only by the visual pass | Phase M maps them, Phase S marks them |
| Full TV episode, 15-45 min | KARGIN SHOW 26, Gor Simonyan 28, Ando Arakelian 10, others | 96 videos, 2,494 min | Phase M |
| Kargin Kaset tape, 45+ min | Gor Simonyan 44, Ando Arakelian 31, Kargin INSTA 10 | 100 videos, 6,842 min; the 49 Kaset-titled ones are tapes 1-10 uploaded 2-6 times each | Phase M, one copy per tape |
| Short compilation titled as one ("best of", "top", "bocer") | Gor Simonyan 14, Kargin Haxordum Unofficial 14, Kargin Ej 7 | 67 videos, 286 min | Phase M |
| 8-15 min video not titled as a compilation | Կարգին Shorts 8, ՀայTV 8, Ando 7 | 44 videos, 471 min | Phase M directly. Only 31 archive videos exceed 300 s and every one above 600 s is a compilation, so length alone makes these suspects, and 90 s of audio can't show a second sketch |
| Fragment: a short or a clip of one sketch | Կարգին Shorts, Kargin Club, TOPOVYYEEE | 6,110 shorts | Skip. Deferred: find shorts that match nothing, which could be the only surviving piece of a lost sketch |
| Other shows (Kargin Serial, Azizyanner) | KarginTV and fans | 343 on KarginTV alone | Out of scope |

## 5. Phase 0 - an engine that finds audio anywhere

Every later phase depends on one capability: given a piece of audio, find where it
occurs in a set of recordings, with the time offset. The current check can't do it
(section 2, item 5).

| Step | What | Gate / output |
|---|---|---|
| 0.1 | Ground-truth set: the 23 `duplicate` and 4 `contains` pairs in `data/duplicates.csv`, with their known lags, plus planted tests. Cut 60 s from the middle of 20 archive sketches, re-encode at low bitrate, prepend 20 s of unrelated audio | `data/audio_index/groundtruth.csv` |
| 0.2 | Probe Q13 option (a): install audfprint2 (pin `==`, check its current release first), index the 702, query the ground truth | Recall, false positives, offset error and run time vs the ground truth. Pass = every known pair found within 1 s of its lag, no false hit above the threshold |
| 0.3 | If (a) fails: option (b). Full-length Haitsma-Kalker fingerprints (the code exists in `fingerprint_audio.py`) plus an inverted index of the 32-bit sub-fingerprints with offset voting, the textbook lookup for this fingerprint | Same pass bar |
| 0.4 | Verification stays ours: the sample-level cross-correlation from `detect_duplicates.py` stage 3 confirms every hit and refines its lag | Every reported match carries `corr`, `lag_sec`, `overlap_pct` |
| 0.5 | Build the archive index: full-length fingerprints of all 702 files in `data/audio/`. Phase A later adds each candidate's 90 s snippet to the same index, so a compilation window can be looked up against archive sketches and fan uploads in one pass | `data/audio_index/`. Small: 702 x ~1,200 frames x 4 bytes = ~3.4 MB. One sequential process; decoding at 8 kHz mono takes minutes, not hours (guess) |
| 0.6 | Close the 2026-08-01 gap: run the engine over the 31 archive videos above 300 s | The 8 archive compilations mapped; they enter the Phase M pool (M1) with their timelines half done |

Load: single process, sequential. No multi-core spike, so no ask needed.

Where the code goes: the engine and the archive index become part of adding ANY
sketch in the future (B4 uses them), so they are load-bearing and belong in top-level
`scripts/`. The candidate triage, matching and review tools are discovery tooling and
go in `scripts/non_essential/` with README entries. Every new script follows the
usual rules: logging to `logs/<name>.log`, progress with an ETA, runtime in the
docstring, dependencies pinned with `==`, and loud failure.

## 6. Phase A - standalone candidates

Goal: a reviewed list of new standalone sketches, each with one chosen upload,
before any archive file changes.

| Step | What | How | Gate / output |
|---|---|---|---|
| A1 | Candidate list | New `scripts/non_essential/triage_candidates.py` over the scout CSV: 60-480 s, not Serial/Azizyanner, not compilation-titled, not shorts; tag the series guess. Anything 480-900 s goes to the Phase M pool instead | `data/candidates/candidates.csv`, about 1,900 rows |
| A2 | KarginTV rows | The 14 in-scope KarginTV uploads (6 Haghordum, 8 Multer; Sketch Show is out, Q5) join the list tagged `source=kargintv`. They are matched like everything else, because KarginTV re-uploads its own sketches (all 23 archive duplicate pairs are KarginTV vs KarginTV). They just need no Q8 choice, since an official copy wins | Rows tagged `source=kargintv` |
| A3 | Screening audio | New downloader: the first 90 s of audio per candidate into `data/candidates/audio/` (gitignored), low bitrate. Resume-safe, and stops on YouTube's bot check like `download_audio.py`. Check yt-dlp's partial-download option in Context7 before writing it. ~2,000 requests will hit YouTube's bot check at some point, so pace the requests and expect the run to span several sessions | About 1.5 GB. Guess: 3-5 h of downloading, spread over days. Fingerprints go into the index; the audio itself is deleted by exact path, with your OK, once A4's matches are saved (Q9) |
| A4 | Match | The Phase 0 engine: each candidate's 90 s against the full archive index (it's found wherever in a sketch it sits, which also fixes the long-intro case), and candidates against each other | `data/candidates/matches.csv`: `have` (+ archive id and offset), `new`, plus a cluster id for candidates that are copies of each other |
| A5 | One upload per new sketch | Apply Q8 per cluster, hard requirements first: the metadata already holds `embeddable`, `region_restriction`, `content_rating` and `availability` for every scout video | `canonical` flag; the other cluster members kept as `alternate` (Q16) |
| A6 | **Visual review 1: triage (you)** | A small local Flask page in the existing `review` dependency group, bound to 127.0.0.1, saving straight to the decisions file (no browser download, so nothing goes through the Downloads folder). Per cluster: thumbnail, title, channel, duration, the match verdict, and the canonical upload playing in an embed, which also proves it embeds. You answer: in scope (Q5)? one sketch, not a compilation? watchable copy? really not in the archive? Note titles that need a curated version (Q18) | `data/candidates/decisions.csv`. This is the backstop for whatever the engine gets wrong |

Phase A output is the first honest answer to "how many standalone sketches are we missing".

## 7. Phase M - mapping compilations, episodes and tapes

Goal: for every multi-sketch video, a timeline saying which archive sketch plays
when, which parts are unknown, and for each unknown part whether a standalone upload
of it exists anywhere.

| Step | What | How | Gate / output |
|---|---|---|---|
| M1 | Pool | Section 4: 96 episodes, 100 tapes, 67 short compilations, the 44 videos of 8-15 min, and the archive's 8 | `data/compilations/pool.csv`, about 315 videos |
| M2 | Collapse copies | Same Kaset number with duration within ~10 s is a copy (49 copies of 10 tapes). Confirm with the engine on the first few minutes, keep the best copy by Q8. Do the same for KARGIN SHOW episodes re-uploaded by others | About 40 fewer videos (~13%) from the tapes alone; more if episodes repeat |
| M3 | Full audio | Download the whole audio at low bitrate (fingerprints use 8 kHz mono) into `data/compilations/audio/` (gitignored). In this order: KARGIN SHOW episodes (your friends' `t=939` links point inside them), one copy of each Kaset tape, then fan compilations. Same pacing and bot-check stop as A3 | At most 3.5 GB, less after M2. Background, resume-safe, spread over sessions. With only 16 GB free (Q9), download in priority batches, and delete a batch's audio by exact path, with your OK, once its timelines are saved |
| M4 | Timeline | Slide each video's audio through the engine in ~10 s windows. Each window is looked up in the one index from step 0.5, which holds the archive's full-length fingerprints and every candidate's 90 s snippet. Runs of consecutive hits on the same recording, with a consistent offset, become spans | `data/compilations/timeline.csv`: `compilation_id, start_sec, end_sec, match_kind (archive / candidate / unknown), match_video_id, offset_sec, corr` |
| M5 | Unknown spans | Gaps of 30 s or more with no match. A candidate hit inside a gap means a fan uploaded that sketch on its own: its 90 s snippet shows where it starts, and its duration in the metadata gives the end | Each unknown span is either `has_standalone` (that upload goes to Phase B) or `segment_only` |
| M6 | Boundary hints | ffmpeg `silencedetect` and loudness dips, plus the recurring stings the 2026-08-01 run found (the `partial` relation is shared intros/stings) used as separators | Suggested cut points inside unknown spans; hints only |
| M7 | **Visual review 5: timelines (you)** | Local page per video: a bar of spans (known = sketch title, unknown = highlighted), each span playable in a YouTube embed at `?start=S&end=E` (no video download). For unknown spans: confirm it is a sketch, adjust start and end, say if it is a known sketch the engine missed, or mark it junk (intro, ad, credits) | `data/compilations/decisions.csv` |
| M8 | Result | Three lists: (i) known sketches inside compilations, which become relations for Phase S; (ii) unknown sketches with a standalone upload, which go to Phase B; (iii) segment-only sketches, whose count decides Phase C | Numbers go into the session log and back into this plan |

Guesses, both unmeasured: review takes 1-2 minutes per unknown span, and a 25-minute
KARGIN SHOW episode holds about 6-8 sketches at the archive's median length of 157 s.

## 8. Phase B - adding whole-video sketches

Input: approved standalone sketches from Phase A (A6) and Phase M (M8 ii). Run in
this order. Every script exists and skips work already done, unless marked **new**.

**B0. Preconditions.**
- Git clean, CI green, nothing deploying.
- Disk space per Q9.
- yt-dlp at its current release AND deno installed (_learnings/ 2026-09-03: without both, formats 403 or vanish).
- Check, without `--refresh` (a one-off Data API probe, ~15 quota units), that none of the 702 archive videos now comes back as **unlisted** (section 2, item 2). If one does, stop: every later number would shift.
- **Hardening, decided (Q19):** make `download_audio.py`, `download_video.py` and `fetch_transcripts.py` take each row's number from the `id` column of `kargin_eng.csv` (joined on `video_id`) instead of re-counting filtered rows. That removes the shift risk for good. Add a test (an unlisted row must not move any later number), a DECISIONS entry, and keep the probe above and `audit_audio.py` as belt and braces.

**B1. Rows.**
- **New** `scripts/add_sketch_rows.py`, modelled on `add_status_final.py`: dry run by default; `--write` backs up `kargin_eng.csv` to `data/backups/`, appends rows (`id`, `titles`, `links`, `video_id`, empty curated fields, `status_final=false`, empty `collections`, `series` (Q7)), and refuses to save if any existing cell moved.
- Never run `annotate_kargin_csv.py`.

**B2. Metadata.**
- `uv run python scripts/fetch_youtube_metadata_api.py`, no `--refresh`. It appends in CSV order (verified: existing rows keep their dict position, new ones are added in input order).
- Check: the first 702 rows are byte-identical, and every new row is public, embeddable, not age-restricted, not blocked in Armenia or Germany, with no `fetch_error`.
- **If any new row fails that check, roll the batch back now**, before anything is downloaded: restore `kargin_eng.csv` and `data/youtube_metadata.csv` from the B1 backup, swap in that sketch's alternate (or drop it), and redo B1-B2. Once files exist, a row can't be removed (section 2, item 2).

**B3. Media.**
1. `uv run python scripts/download_audio.py`, then `uv run python scripts/audit_audio.py`. Exit 0 or stop.
2. `uv run python scripts/download_video.py` (360p like the corpus).
3. Compare video and audio stream durations with ffprobe on the new files; more than 2 s apart is a truncated download (_learnings/ 2026-09-03). This needs a small probe script; none exists.

**B4. Duplicates.**
1. `uv run python scripts/fingerprint_audio.py`, then `uv run python scripts/detect_duplicates.py`, plus a Phase 0 engine run of each new file against the archive index.
2. Expect no new `duplicate`. **If one appears, do not delete the row**: its number is already baked into the file names of every later new row. Either (a) roll back the whole batch to the B1 backup, delete only this batch's new files by exact name, and redo B1-B3 without it; or (b) keep it and record it in `duplicate_of`, which first needs a safe writer (section 2, item 7). Use (a) if it is caught before B5, (b) after.

**B5. Transcripts.**
1. `uv run python scripts/fetch_transcripts.py`, then `uv run python scripts/convert_transcripts.py`. Free `hy` captions where they exist.
2. For the rest (Q10), in order:
   - `scripts/build_transcription_batch.py`
   - `scripts/render_transcription_batch.py`
   - **you** upload the mp4 to YouTube, unlisted, language Armenian
   - download the JSON3 captions
   - `scripts/split_batch_transcript.py --captions <file>`. Its duration check must pass (_learnings/ 2026-08-02).

**B6. Contact sheets.**
- `uv run python scripts/build_contact_sheets.py`.
- **Visual review 2 (me):** sample the new sheets; black tiles mean a broken download.

**B7. Visual annotations (Claude usage, ask first).**
- `annotate-sheets` skill: Sonnet waves of 9-12 sheets per agent, about 11k tokens per sheet.
- Then escalate the low-confidence ones to Opus (~14%): 7 per agent, at most 3 at a time, each file written the moment it's done.
- Per 100 sketches: about 9-11 Sonnet agents plus about 2 Opus agents. Each wave gets your OK.

**B8. Text annotations.**
- `uv run python scripts/extract_text_annotations.py --model flash3 <new ids>`, after B5 and B7 (it reads the transcript and the visual annotation).
- Cost: about $0.002 per sketch, logged in `data/gemini_spend_ledger.jsonl`.
- Expect some `PROHIBITED_CONTENT` blocks (12 of 702 last time); record which.

**B9. Embeddings.**
- `uv run python scripts/embed_annotations.py --force` (a full rebuild, about $0.03). Keep its one-vector-per-call assertion (_learnings/ 2026-09-07).
- Then `scripts/non_essential/build_similarity_report.py` to look at the new sketches' neighbours.
- Exclude compilations from the neighbour lists if Phase S marks them (their embeddings are mixtures).

**B10. Songs.**
- `uv run python scripts/sweep_songs.py` in the background. The cycle is about 12 minutes of work, then about 20 minutes of cooldown; it handles the cycles itself.
- Optional: `scripts/fetch_music_credits.py`.

**B11. Actors from text cues, then curation (you).**
1. **New** `scripts/non_essential/prefill_actors.py` (Q11): propose `main_actors` per new sketch from the title, the description and the transcript. Text only, never faces. That covers the "(Hayko Mko)" titles and characters calling each other by the actors' names. It writes proposals as `data/corrections.csv` rows, each with the phrase that matched as evidence, like `seed_collection_candidates.py`. Measured coverage from titles and descriptions alone: 10-15% of candidates.
2. You glance over the proposals, then `scripts/apply_corrections.py` (dry run first, then `--write`).
3. Sketches with no text cue ship untagged (Q11). They're missing from actor pages and the actor filter until tagged later, and `data/candidates/untagged.csv` lists them so nothing is forgotten.
4. The other curated fields are optional, filled over time in `uv run --group review python scripts/review_ui.py`: `roles_names`, `main_actors_count`, `location`, `lighting`, `languages`, `text_common`, `text`, `status_final`.
- This drops the old 2-4 min per sketch of curation before publishing, at the price of incomplete actor data.

**B12. Collections.**
1. `scripts/non_essential/seed_collection_candidates.py`
2. Tick the new rows
3. `scripts/non_essential/apply_collection_candidates.py --write`
4. `scripts/apply_corrections.py --write`
5. `PYTHONPATH=scripts uv run python scripts/build_collections.py`

**B13. Build.**
- `PYTHONPATH=scripts uv run python scripts/build_site_data.py`.
- Read the log, not just the exit code:
  - the totals, and how many have actors, transcripts, visual annotations and neighbours
  - **"top non-allowlist tokens in roles"**: new actors stay off actor pages until added to `ACTOR_ALLOWLIST` in `assemble.py`
- Check that `parse_seq` gives sensible numbers on fan, Multer and Kaset titles (a "Kaset 7" or "#8" must not become "sketch 7"/"sketch 8").
- Q17: add `uploader` to the metadata columns the build reads (`_METADATA_COLS` in `assemble.py`), to `Sketch` in `types.ts`, and a line on the sketch page.

**B14. Site copy.**
- Compute the count in `layout.tsx` and `stats/page.tsx` from the data.
- Reword `about/page.tsx` as history.
- Add an entry to `web/lib/changelog.ts`.
- Q7: `series` in `types.ts`, a facet, and a label on cards and the sketch page.
- At the end, update `CLAUDE.md` (layout counts) and `HANDOFF.md`.

**B15. Tests.**
- `uv run pytest`
- In `web/`: `npm test`, `npm run lint`, `npx tsc --noEmit`, `npm run test:rules`, `npm run build`
- In `bot/`: `npm test`
- Low RAM makes vitest fail in bulk; rerun once before debugging.

**B16. Visual review 4: the site, locally (me, Playwright).**
Serve with `python -m http.server 3005 --bind 127.0.0.1 --directory web/out` (never from inside `web/out`), then check:
- Search finds a new sketch by an Armenian quote and by a Latin spelling.
- A new sketch page renders cleanly with no actors or curated text.
- Actor pages pick up the new sketches.
- The stats numbers add up.
- Nothing scrolls sideways at 390 px.
- The home page's transferred size (compressed JS plus data), measured before and after (section 2, item 12). If it grows by more than ~25%, stop and plan a payload split before shipping. That would be its own decision.
- Every new sketch's player actually plays (embedding, region, age).

**B17. Ship.**
1. Topic commits. DECISIONS #19 already records the interview answers; add entries for what implementation decides on its own: the Q13 probe result, the B0 hardening, the `series` values, and the Q18 outcome.
2. One push, which is a prod deploy (Pages + Firestore sync). Never push again while it runs.
3. The Firestore sync log must show N adds and 0 deletes.

**B18. Bot.**
- `uv run python scripts/deploy_bot.py v4`.
- Then `/health` must return ok, and `getWebhookInfo` must show 0 pending and no error.
- Then a real Telegram search that only a new sketch can answer.

**B19. Live check and docs.**
- Live spot checks as in B16.
- Session log, `HANDOFF.md`, learnings.

**B20. Dead-video watch (new, recurring).**
- **New** `scripts/check_availability.py`: Data API `videos.list` over every archive video (1 quota unit per 50, so ~16-20 units for ~900 videos).
- It reports anything no longer public, embeddable and unblocked, and never writes `data/youtube_metadata.csv` (section 2, item 2).
- Run it monthly, or as a step in the usage check.
- First run, about 4 weeks after the scout: also re-check all 9,813 scout videos (~200 units) to **measure** how often fan uploads actually die. Q16 (b) or (c) is only worth building if that number is high.

## 9. Phase S - compilations on the site

For Q14 (a). It can ship before Phase B, since it only needs Phase 0 step 0.6 and the M7
review of the archive's own 8 compilations.

| Step | What |
|---|---|
| S1 | Data: a `kind` column in `kargin_eng.csv` (empty = sketch, `compilation`), written by a **new** column script modelled on `add_collections_column.py` and set through `corrections.csv`. `data/compilations/timeline.csv` is committed (small) |
| S2 | Build: **new** `scripts/kargin_build/compilations.py` folds the timeline into `sketches.json`. A compilation carries `kind` and `contains: [{id, startSec}]`; a sketch inside one carries `alsoIn: [{id, startSec}]`. It fails loudly on an id that isn't a sketch (same rule as `neighbors.py`). When one stretch matches two archive sketches that are duplicates of each other (seen in `mrIUW3fCUUo`: sketches 107 and 430, 593 and 108), list the pair once, not as two sketches |
| S3 | Web: `types.ts`; a "compilation" label on the card and the sketch page; a "this video contains" list on the page linking each sketch and the moment it plays (`youtu.be/<id>?t=S`); exclude compilations from `/random`, from the sketch count and stats, and from neighbour lists. Search unchanged |
| S4 | Bot: the same label; exclude from `/random` |
| S5 | Tests for the build module (missing id, overlapping spans) and for the web helpers |
| S6 | DECISIONS entry (Q14, Q15) and a changelog entry |

## 10. Phase C - sketches that exist only inside a longer video

In scope regardless of Phase M's count (Q5). Write its spec in
`docs/superpowers/specs/` while Phase M runs, so building can start as soon as M7's
boundaries exist. The spec covers:

- **A stable archive id that is not the YouTube video id** (Q16). One design for two jobs: a segment needs an id of its own, and a dead upload must be swappable for an alternate without changing the sketch's URL. It touches routes, Firestore doc ids, hearts and event logs, and bot callback data (64-byte cap). The existing 702 need a migration: their current URLs (`/sketch/<videoId>`) must keep working, through redirects in `web/firebase.json` or an alias table, and their hearts and events must map across.
- **`startSec` / `endSec`** on the sketch. The player embed uses `?start=&end=` and links use `?t=`.
- **Per-segment media.** Audio cut per segment for fingerprints, songs and transcripts, and contact sheets built from the segment, not the whole video.
- **The 999 ceiling** (section 2, item 3) and the `NNN_` file naming for segments.

The boundaries come from the M7 review, so Phase C has no detection step of its own.

## 11. Money, Claude usage, time, disk

| Item | Estimate | Basis |
|---|---|---|
| Gemini text annotations | ~$0.002 / sketch | _learnings/ 2026-09-07 (A/B on flash3, thinking off) |
| Embeddings, full rebuild | ~$0.03 | probe cost ~$0.0001 per 3 docs |
| YouTube Data API, Shazam, audfprint | $0 | free quota, free tools |
| Data API quota | B2 ~10 units, B0 probe ~15, B20 ~20 per run (~200 with the scout re-check), out of 10,000/day | 1 unit per 50 videos |
| Disk, everything at once | ~8.5 GB of the 16 GB free (A3 + M3 + ~300 sketches) | sum of the rows below; see Q9 |
| Visual annotation | ~11k Claude tokens / sheet + Opus for ~14% | _learnings/ 2026-09-03/04 |
| Disk, added sketches | ~11.5 MB each | measured |
| Disk, screening | ~1.5 GB (A3) + up to 3.5 GB (M3) | measured sizes x counts |
| Engine build, archive index | minutes, one process | guess |
| Screening downloads | 3-5 h background | guess |
| Compilation audio downloads | several hours background | guess, 168 h of audio before M2 |
| Shazam sweep | hours, background | throttle-bound |
| Batch ASR turnaround | hours to a day | guess |
| Your review time | triage ~30 s / cluster; timelines 1-2 min / unknown span; a glance at actor proposals per sketch; other curation optional, later (Q11) | guess |

## 12. Done checklists

A new sketch is done when it has:

- [ ] a row in `kargin_eng.csv` (id, links, video_id, curated fields, `status_final`, `series`)
- [ ] a row in `data/youtube_metadata.csv`: public, embeddable, not age-restricted, not blocked in Armenia or Germany
- [ ] its alternate uploads, if any, recorded in `data/candidates/` (Q16)
- [ ] `data/audio/NNN_*` passing `audit_audio.py`, and a fingerprint in the archive index
- [ ] `data/video/NNN_*.mp4` with matching stream durations
- [ ] no `duplicate` pair in `data/duplicates.csv`
- [ ] a transcript in `data/transcripts/`, or a recorded reason it has none
- [ ] `data/contact_sheets/NNN_*.jpg` with no black tiles
- [ ] `data/visual_annotations/NNN_<id>.json`, above low confidence after escalation
- [ ] `data/text_annotations/NNN_<id>__flash3-nothink.json`, or a recorded block
- [ ] a vector in `data/embeddings/` and a `top_neighbors.json` entry
- [ ] Shazam coverage in `data/song_matches.csv`
- [ ] actors tagged where text cues allow, and actor tokens on `ACTOR_ALLOWLIST`; otherwise listed in `data/candidates/untagged.csv` (Q11)
- [ ] `series` set (Q7) and `uploader` shipped (Q17)
- [ ] collection membership reviewed
- [ ] an entry in `sketches.json` (with `uploader`), a Firestore doc, and in the deployed bot image
- [ ] a player that plays on the live site, and a place in the B20 availability watch

A multi-sketch video is done when it has:

- [ ] a row in `data/compilations/pool.csv`, and its copies collapsed
- [ ] a timeline in `data/compilations/timeline.csv` with every span either matched or reviewed
- [ ] every unknown span resolved in `decisions.csv` as known (engine miss), standalone upload (sent to Phase B), segment-only (counted for Phase C), or junk
- [ ] if it is one of the archive's own: `kind=compilation`, with `contains` / `alsoIn` showing on the site

## 13. Gotchas to carry through

From _learnings/, HANDOFF and this session:

- yt-dlp needs deno. Video selectors need `vcodec^=avc1` and `protocol=https`. Compare stream durations; the container duration lies.
- Never run `annotate_kargin_csv.py`. Never `--refresh` metadata casually: it replaces a dead video's metadata with an empty error row. `audit_audio.py` gates every fetch.
- Once a new row's files exist, never delete the row: every later new row's number is baked into its file names. Roll the batch back from the B1 backup instead.
- An **unlisted** archive video shifts every later number. Deleted and private ones don't (empty `availability` counts as public).
- YouTube's bot check ("Sign in to confirm you're not a bot") will hit a ~2,000-request run. The downloaders stop on it by design; pace the requests and resume later, never hammer through.
- The engine's verdict is the cross-correlation, never the fingerprint score alone. A frame-quantised score swings 5x on alignment luck alone.
- Classify "same audio" by duration: about the same duration = `duplicate`, much longer = `contains`, a shared slice = `partial` (stings and intros).
- `gemini-embedding-2` returns one vector for a batch without saying so. Keep one request per document.
- `PROHIBITED_CONTENT` is decided on the prompt, so `safety_settings` cannot fix it; rephrase.
- Never read success from a piped exit code (`| grep`, `| tail`).
- The Shazam throttle budget survives a killed process; probe before resuming.
- `uv run` sometimes stalls ~2 min on this machine; use `.venv/Scripts/python.exe` for chained commands.
- A push to `main` is a prod deploy. `[skip ci]` is for docs-only commits.
- Opus vision agents stall. Write each file as soon as it's done, and give each agent uniquely named helper files.
- The 999 ceiling, the 16 GB of free disk, and the 64-byte bot callback cap if Phase C happens.
- Never list `.playwright-mcp/` or `Downloads`; open files there by exact name.

## 14. Sources

Checked 2026-11-03 for Q13:

- Panako 2.0 notes (2021): https://0110.be/date/2021/11 and readme https://0110.be/releases/Panako/Panako-1.5/readme.html
- audfprint: https://github.com/dpwe/audfprint/ and the packaged fork https://pypi.org/project/audfprint2/
- Olaf: https://joss.theoj.org/papers/10.21105/joss.05459.pdf (JOSS 2023) and activity snapshot https://summary.ecosyste.ms/projects/357093

## 15. Review log

Review of this plan against the code, 2026-11-03, after the compilations revision.
Each claim the plan leans on was re-checked: `fetch_youtube_metadata_api.py` (row
order, `error_row`), `download_audio.py` (the `availability` filter),
`WatchView.tsx` (the player), `web/lib/data.ts` (the payload import), and
`data/youtube_metadata.csv` (embeddable/availability counts).

The "you should know" note under the previous reply raised fan-upload link rot. Its
point about broken players is right. Its claim that a vanished video shifts the
numbering is only half right: deleted and private videos keep their slot, unlisted
ones shift it. Both are now in the plan.

| # | Severity | Finding | Fixed where |
|---|---|---|---|
| R1 | Critical | The site's player is a YouTube iframe, so a non-embeddable, region-blocked or age-restricted fan upload plays nothing. Nothing in the plan checked it | Section 2 item 10, Q8 hard requirements, A5, A6, B2, B16, checklist |
| R2 | Critical | B4 said "drop the row" on a late duplicate. Each new row's number is in its file names, so removing one shifts every later new row onto the wrong files | B2 rollback rule, B4 options (a)/(b), gotchas |
| R3 | High | Dead fan uploads: no detection, and no answer for what the page shows, given the sketch id is the video id | Section 2 item 11, Q16, B20, alternates kept in A5 |
| R4 | High | Section 2 item 2 was wrong in detail: private and deleted keep their slot; unlisted shifts; `--refresh` blanks dead rows | Section 2 item 2, B0 probe + optional hardening, gotchas |
| R5 | High | A4 claimed to flag compilations from 90 s of audio, which can't show a second sketch | 8-15 min videos go to Phase M (section 4, A1, M1); the `contains-2+` verdict is removed from A4 |
| R6 | High | A2 skipped matching for KarginTV "because official", yet all 23 duplicate pairs in the archive are KarginTV vs KarginTV | Section 4, A2 |
| R7 | Medium | The archive ships inside the home page's JavaScript (2.76 MB for 702); growth was never measured | Section 2 item 12, B16 size gate |
| R8 | Medium | M4/M5 didn't say which way the lookup goes, and the candidate pool holds only 90 s snippets | Step 0.5 (one index with both), M4, M5 |
| R9 | Medium | Fan uploads bring the fan's views and upload date into the stats, and no attribution | Q17, B13 |
| R10 | Medium | Fan titles may be clickbait, and titles aren't editable on purpose | Q18, noted during A6 |
| R11 | Medium | ~2,000 downloads will trip YouTube's bot check; the plan assumed one smooth run | A3, M3, gotchas |
| R12 | Low | The engine is load-bearing for future additions but was placed in `non_essential/` by implication; new-script conventions unstated | Placement note under Phase 0 |
| R13 | Low | The A6 review page was unspecified, and a static page would push decisions through a browser download | A6: local Flask page writing the file directly |
| R14 | Low | Q13 called audfprint "maintained" while saying its maintenance is unverified | Q13 reworded |
| R15 | Low | M2 claimed the pool drops "by about a third"; collapsing 49 tape copies to 10 removes ~40 of ~315 (~13%) | M2 |
| R16 | Low | Step 0.6 pointed at M6 (boundary hints) instead of the M1 pool | 0.6 |
| R17 | Low | Q9 only counted Phase M's disk; the total is ~8.5 GB of 16 GB | Q9, section 11 |

What this review did NOT do: run any of the steps, check `parse_seq` on real Sketch
Show titles, or measure the actual home-page transfer size. Those are checks inside
the plan (B13, B16). A subagent with no knowledge of this plan could still give an
independent read (Q12).

## 16. Progress log

Newest last. Numbers are measured unless marked as a guess.

**2026-11-03, Phase 0 (engine): done, Q13 decided.**
- **Probe:** audfprint2 0.1.2 against 128 ground-truth queries. It found 67/67
  unmodified positives at ≥ 2.0 matched hashes per query second: 23/23 duplicates,
  4/4 contains, 20/20 mid-sketch clips, 20/20 behind a noise intro. The weakest true
  match scored 3.24/s, the strongest of 102 spurious hits 1.14/s, and the worst offset
  error was 0.02 s. Sped-up clips failed: 0/40.
- **Real fan uploads:** 78 of 187 matched the archive, and none of the 109 unmatched
  matched after a ±3/5% speed correction, so speed changes are accepted as rare. A
  ±1.5% re-check is running.
- **Adopted:** `scripts/audio_index.py` with the `match` dependency group,
  DECISIONS #21. The engine's archive index builds in 556 s alone, ~980 s under load.
  The probe data is in `data/audio_index/probe_2026-11-03/`, its scripts in
  `scripts/archive/`.
- **Side effect:** the probe already found sketches deep inside the archive's own
  compilations, e.g. `uObBR5ju488` at 9:31 inside `E0apclx3wqU` and `YP4Q6dkI_0o` at
  8:17 inside `mrIUW3fCUUo`.

**2026-11-03, Q19 hardening: done.** `scripts/archive_ids.py`; the three downloaders
take the file number from `id` (DECISIONS #20). This was safe because `id` already
equalled every file prefix (702 audio, 704 video, 702 sheets, 484 transcripts), and
it is pinned by a test. 7 new tests.

**2026-11-03, A1 triage: done, then tightened.**
- `scripts/non_essential/triage_candidates.py` first gave 1,917 standalone
  candidates, a pool of 327 and 7,577 skips.
- **The owner asked whether we were downloading non-Kargin material.** We were: 927
  candidates (48%) had no Kargin marker in the title, 558 of them from just two
  channels (Կարգին Shorts, Kargin Club), largely other shows hashtagged `#Կարգին`
  (Bolola episodes, Vitamin Club, Women's Club, Eleni oragir).
- **Fix:** an other-show title filter applied only to unmarked titles. It removed 266,
  leaving **1,651 candidates** (haghordum 700, kaset 273, multer 17, unclear 661) and
  a **pool of 298** (9,420 min).
- **The 661 unclear titles wait.** Their download is decided per channel on evidence:
  how often that channel's unmarked uploads match the archive.

**2026-11-03, A3 screening: in progress.** `scripts/non_essential/screen_audio.py`.
- Each clip is exactly 90.0 s, ~549 KB, ~7.5 s with pacing.
- Marked series download first (990 rows). 518 + 74 unclear clips were on disk when
  the order changed.
- 5 transient ffmpeg failures; one, re-run by hand, worked. The screener retries them
  on its next run.

**2026-11-03, A5 data: done.** `scripts/non_essential/fetch_candidate_status.py` →
`data/candidates/status.csv`.
- Of 2,244 candidate and pool videos, 2,229 pass the hard requirements and 5 fail
  them: 1 not embeddable, 2 age-restricted, 2 blocked in Armenia, 1 blocked in Germany.
  1,405 are HD.
- 10 were already gone a week after the scout, all from one channel
  (©Stepanyan_Production©) and all non-Kargin. That's one channel cleaning up, so it
  is NOT a link-rot rate; B20 is still the real measurement.

**2026-11-03, tools ready, waiting on data:**
- `scripts/non_essential/match_candidates.py` (A4 verdicts + A5 copy choice, 6 tests)
- `scripts/non_essential/map_compilations.py` (M4/M5 timelines confirmed by
  cross-correlation, 1 test)
- `scripts/non_essential/triage_ui.py` + `scripts/review_templates/triage.html` (A6
  page: keyboard-driven, appends to `data/candidates/decisions.csv`)

**2026-11-03, speed question closed.** A second pass on 494 real fan clips (170
matched): all 324 unmatched re-queried at ±1.5% (both kinds), **0** matched. With the
earlier ±3/5% pass (0 of 109), no speed-shifted fan copy has been seen.
`data/audio_index/probe_2026-11-03/real_speed_check.json`.

**2026-11-03, step 0.6, the archive's own compilations: mapped.**
`scripts/non_essential/map_compilations.py --set archive` → `data/compilations/timeline_archive.csv`.
- **The 6 long ones (566-1,177 s) are almost entirely sketches we already have:** 69
  spans covering **51 distinct archive sketches**. The unknown gaps are only 31-54 s
  each (7 gaps, 278 s in all), probably intros, links between sketches or very short
  bits. They go to the M7 review.
- **`VFajwBRJxc4` (168 s) and `aOZ3vbc1iFA` (237 s) are different.** The visual pass
  calls each "a compilation of unrelated segments", yet no segment of either exists
  anywhere else in the archive. They are short compilations of sketches the archive
  doesn't hold on their own: the first concrete Phase C material, unless fans
  uploaded the pieces separately (Phase M step M5 will check).
- **Bug found and fixed in my own verification.** One correlation over a whole matched
  stretch rejected 5 genuine hits in `Fyc5VWnAMog` (thousands of matched hashes,
  correlation 0.13-0.39). Measured cause: a clock drift of ~0.002% (the lag walks -6 →
  -2 ms over 200 s), which puts long stretches out of sample alignment; 10 s windows
  scored 0.95-0.99. Verification is now windowed (10 s windows, ±0.5 s local lag
  search, at least half the windows ≥ 0.6), with a test reproducing the measured drift.
  The windowed check is also stricter where it should be. In `mrIUW3fCUUo` it rejected
  weaker secondary alignments (60-86 hashes, no window agreeing) of sketches whose main
  alignment it confirmed: 162-338 s is sketch 107 (`xaVdaU-N7Gw`) and 196-339 s is
  sketch 430 (`sSIXTq8KlTw`), every window agreeing. The two are themselves an archive
  duplicate pair, as are 593/108 at 354-402 s. (An earlier note in the chat called this
  stretch an unknown sketch; that was wrong.)

**2026-11-03, the per-channel gate (DECISIONS #22): done.** 187 unmarked uploads
sampled (176 matchable, 11 gone, private or sign-in only).
- **keep:** 9 channels, 222 titles. Կարգին Shorts 3/8, ՀայTV 5/7, Hayastan
  Armenia1991 7/8, Kargin Tube 5/8.
- **skip:** 42 channels, 428 titles. Kargin Club 1/8 with 212 titles,
  "KARGIN “KARGIN HAXORDUM” ЮМОР" 0/8.
- **triage:** 3 Kaset-heavy channels, 11 titles.

**2026-11-03, Phase A matching (A3-A5): done for the standalone candidates.**
1,356 screening clips matched against the archive (~0.8 s each). A candidate
self-index of 1,207 clips was matched against itself to cluster copies.
`data/candidates/matches.csv`:

| Verdict | Candidates |
|---|---|
| `have` | 519, re-uploads of **322 distinct archive sketches** |
| **`new`** | **681 in 432 clusters**: 143 Haghordum, 188 Kaset, 10 Multer, 91 unclear (from kept channels) |
| `new*` | 12, clustered with a `have`: probably a re-cut |
| `gated_out` | 414 |
| `unavailable` | 25 |

Only 4 clusters have no playable copy.

**2026-11-03, A6 triage page: ready and tested.** `triage_ui.py` with 469 clusters
(new + new* + 30 spot-checks), official uploads first.
- Tested in Playwright against real data with a scratch decisions file:
  1. Save moves on.
  2. `b` swaps to the next copy.
  3. The chosen copy and the bad copies land in the CSV.
- The first test caught a 5.5 s queue build on every save; it's now 0.03 s, built in
  plain Python and cached.
- The clustering visibly works: KarginTV's "Kargin Multer - Napy" sits with two fan
  copies titled "Կարգին մուկտ նապը" and "Kargin multer. Napastak", all 234.0 s.
- **Next for the owner:** `uv run --group review python scripts/non_essential/triage_ui.py`,
  open http://127.0.0.1:5056.

**2026-11-03, M2/M3: running.** `collapse_pool.py` merged 21 exact copies (1,032 min).
266 pool videos (8,231 min, ~2.9 GB) are downloading in full.

**2026-11-03, a mistake of mine, fixed.** The speed test wrote every variant as an
uncompressed WAV and never deleted them: 2,168 files, **12 GB**, which took the disk
from 16 GB free to 5.5 GB (99% full) while downloads ran. I deleted that one scratchpad
folder by its literal path (throwaway intermediates; the results were already saved),
and the disk is back to 18 GB free. Rule for next time: generate, use and delete each
variant (or keep it in memory). Never accumulate intermediates on this disk.

**2026-11-03, M4 made affordable.** Measured costs: a whole-file decode at 8 kHz takes
~12 s per 20 min of audio, and each windowed reference read ~0.38 s (mostly ffmpeg
start-up). Verifying every hit would have taken ~5.5 h on the fan pool. On the
archive's own compilations, all 69 confirmed hits scored ≥ 6.22 matched hashes per
second of stretch and all 5 rejected ones ≤ 0.96/s. So hits ≥ 4/s are now accepted on
the fingerprint, < 1.5/s rejected on it, and only the band between gets the windowed
check (the query is decoded only if some hit needs it). The archive set went from 215 s
to 9 s with an identical timeline; a rerun was diffed against the earlier output. If
the pool produces many hits in the 1.5-4 band, look at them before trusting the cut.

**2026-11-03, M3 pool download: 257 of 266.**
- The first pass got 248; 16 of its 18 failures were "unable to download video data:
  HTTP Error" partway through long downloads.
- A retry on the old yt-dlp (2026.08.19) recovered 4. The current release (2026.10.26,
  tested first in a throwaway venv) recovered 5 more, including a 106-minute tape that
  failed every time before. So the project pin is bumped to `yt-dlp==2026.10.26`.
- **9 remain:** 7 still get 403 (including `r-SKAxdW_pM`, a KARGIN SHOW episode linked
  in the friends' chat; its first half `52X4-E6--yI` is on disk) and 2 are gone.

**2026-11-03, gate re-sampled.** Kargin Club is borderline at 4/21 (19%) and is referred
to the owner (DECISIONS #22).

**2026-11-03, independent review of the triage page: 12 findings, all fixed and re-tested.**
A reviewer agent with no stake in the code confirmed each finding against a scratch
server; each fix was then re-tested here in Playwright, and the server-side ones with curl.
- **Fixed (would have lost or corrupted work):**
  - typed notes were wiped by any shortcut;
  - a double Enter saved the next cluster unseen;
  - Ctrl+C / Ctrl+A changed answers;
  - `new*` clusters played the already-archived copy;
  - one cluster was queued twice (as `new*` and as a spot-check);
  - a chosen copy could also be marked bad;
  - overlapping saves could drop a row;
  - a `text/plain` POST from any other open page was accepted.
- **Fixed (cost time):**
  - clicking the YouTube player killed every shortcut (there's now a "keys on/OFF"
    indicator and focus comes back after a click);
  - the Armenian keyboard layout killed shortcuts (they now map by physical key);
  - a failed save still said "saved";
  - the sidebar highlight didn't follow, and saving didn't wrap back to skipped items.
- **Upstream fix it exposed:** union-find linked any two clips sharing audio, and one
  uploader opens every Kaset clip with the same ~25 s, which chained tapes 3, 4 and 5
  into one cluster (links 22-28 s at offset ~0; the real copy pair in it shared 71 s).
  Copies now need a matched stretch covering at least half the clip (12% of the 1,285
  links fell below). After the fix: `new` 689 in 446 clusters (Haghordum 150, Kaset 193,
  Multer 10, unclear 93), `have` 525, `new*` 4. **The triage queue is 478** (446 + 2 +
  30 spot-checks), with no duplicates.

**2026-11-03, two more independent reviews (code and method); conclusions corrected.**
The owner offered spare Claude usage, so three reviewers with no stake in the work
read the code, the triage page and the method. Their findings were checked against the
data before acting.

- **Code: 12 findings, the ones that changed results fixed.**
  - **Hit caps.** 40 per long video and 10 per clip left real sketches out (7 of 8
    archive compilations, 38 of 59 pool videos, 472 of 1,390 clips saturated). Caps now
    scale with length, and saturation logs an ERROR.
  - **Trimmed stretches.** audfprint's 5% trim made **5 of the 7 "unknown gaps" in the
    archive's compilations artifacts**; my "7 gaps, 278 s" is withdrawn. Full extents
    now, clipped to where the reference can lie.
  - **Highlight reels** of 3-20 s pieces were invisible; short dense pieces are now
    accepted when a sample-level correlation confirms them.
  - **A 16 s jingle could make a `have`.**
  - **Transient download errors counted as "gone"**: only gone, private, sign-in and
    age failures count now.
  - **Archive duplicate pairs counted as two sketches.**
  - **Channels were keyed by non-unique titles** (two different "ԿԱՐԳԻՆ BOT").
  - **The gate sample re-picked itself.** It's append-only now, restored to the
    original 187 plus the 85 extra.
  - **Mining required embeddable videos**, which it doesn't need.
  - **Ingest only worked from the repo root.**
- **Method: the biggest correction.** On real fan data the 2.0 threshold has **no gap**:
  244 of 1,390 clips score 1.0-3.0, mostly **montage shorts** that cut one sketch into
  pieces, each under 2.0.
  - **Fix:** per-sketch scoring (sum over all stretches on one archive sketch, ≥ 2.0,
    covering ≥ 30% of the clip in distinct seconds of the sketch). The reviewer measured
    it turning ~138 `new` clips (~114 clusters) into `have`.
  - **Kargin Club** scores 12/21 under it (not 4/21), so the gate's skip was wrong; M A R C
    flips too.
  - **`#karginserial` hashtag spam** dropped 21 real candidates; out-of-scope checks now
    ignore hashtags.
  - **Fragments:** 169 of 448 `new` clusters have no copy over 75 s, so the triage page
    gets a "Only a piece of a sketch" answer.
  - **The density shortcut is unproven on fan material** (shared intros score up to
    60/s). A fan clip now counts as a standalone copy only if it's ≥ 50% covered, and 50
    accepted plus 50 rejected shortcut decisions are re-checked the slow way into
    `audit_<set>.csv`.
- **Speed: the earlier "no speed-shifted fan copies" is withdrawn.** Measured tolerance:
  tape speed (pitch moves) **±0.5%** (half lost at ±1%, all at ±2%); tempo only ±3%. The
  earlier ±1.5/3/5% grid had gaps. A 1%-step sweep on 100 leftover `new` clips follows
  (`speed_sweep.py`, one temporary file at a time).
- **The engine found an archive duplicate pair August missed:** sketches 107
  (`xaVdaU-N7Gw`) and 430 (`sSIXTq8KlTw`) cover the same stretch of `mrIUW3fCUUo`,
  every window agreeing.
- **Doubtful:** `aOZ3vbc1iFA` may be one sketch rather than a compilation; a 249 s fan
  upload matches it from 3 s to 79 s.

**2026-11-03 night, overnight chain steps 1-9: done.** Retries and hashtag-recovered
titles downloaded, the gate re-decided under the per-sketch rule, the kept channels'
remaining unmarked titles downloaded and matched, the candidate self-match redone.
- **Gate** (DECISIONS #22, final table there): keep 11 channels / 452 titles (Kargin Club
  14/24, now kept), skip 38 / 192, triage 8 / 19.
- **Verdicts** (`matches.csv`): new 635 in 417 clusters (Haghordum 111, Kaset 191,
  Multer 10, unclear 105), have 831 (437 archive sketches covered), new* 1, gated_out
  182, unavailable 13, no_clip 10. 23 canonicals have no playable copy in their cluster.
- **Triage queue:** 418 clusters plus 30 spot-checks.
- **Archive compilations (step 0.6, redone with full extents):** 8 videos, 79 confirmed
  spans, 4 `unknown` gaps (485 s: two in `Fyc5VWnAMog`, all of `VFajwBRJxc4` and of
  `aOZ3vbc1iFA`).
- **The first shortcut audit took 2.5 h:** it seeked into 20-95 min compilations at ~8 s a
  call. It now decodes each query once. I stopped the chain to fix it.

**2026-11-04, the owner's answers (Q20-Q23) and what changed tonight.**
- **Q20, commit and push:** after the pool mapping and the speed sweep finish. The pool
  mapping is much slower than I first said: ~65 s of matching per video per index, so
  ~4.5 h per index, finishing in the morning.
- **Q21, No Comment stage show: out of scope** (DECISIONS #23). Pool 299 → 288 rows,
  download list 267 → 256. `map_compilations.py --set pool` now maps only the download
  list, so the stage show's audio on disk is ignored.
- **Q22, sketches 107/430: verified and recorded.** All of 430 sits inside 107 at
  +19.41 s; 107 has a ~19 s studio intro first. Windowed correlation 0.987-0.996 on 16/16
  windows. `duplicate_of` set on both rows via the corrections overlay (2 cells changed),
  one row added to `duplicates.csv` (canonical 430, the most viewed). Verdicts unchanged;
  "archive sketches covered" 438 → 437.
- **Q23, learnings:** LEARNINGS.md split into `_learnings/` (180 files, one per lesson,
  dated by git blame; 0 of 318 lines lost), four new lessons added, CLAUDE.md and the
  live references repointed.
- **Hit caps fixed for good.** The chain logged 28 "real matches may be cut" ERRORs that
  nobody acted on. audfprint computes every hit anyway and its cap only slices the list,
  so `audio_index.match()` now keeps every hit with >= 20 hashes plus the strongest up to
  the cap. (A first fix that re-matched with a doubled cap redid the whole analysis for
  identical results; replaced the same night.) All rows the cap may have cut were
  re-matched: 4 + 2 candidate-vs-archive, 3 + 59 self-match, 3 archive compilations,
  3 pool videos. No verdict, cluster, canonical or archive-timeline span moved.
- **Why the pool mapping was slow, and the fix (owner asked).** Profiled: ~87% of a match
  is analysing the query (audfprint analyses queries at 4 sub-frame shifts), the lookup is
  the rest, and the analysis was being redone for the second index. Query hashes are now
  cached in `data/compilations/hashes/` (gitignored), so the candidates pass costs only
  lookups for every video analysed in this run. Restarted 00:44: ~181 videos × ~65 s for
  the archive pass (~3.3 h), then the candidates pass (~2 h: the 79 videos done before
  the cache existed are analysed once more, the other ~181 cost ~11 s each), then confirm
  and audit (~1-1.5 h, a guess). Expected to finish around 07:00-07:30 instead of ~10:00. Not done: `shifts=1` (~4x faster analysis, but needs a
  new ground-truth probe), and parallel mappers (~2.4 GB each, 1.5 GB RAM free).
- **Kaset tapes DO contain archive sketches (preliminary).** 13 of the first 19 Kaset
  tapes mapped have archive stretches of >= 20 s at 10-14 hashes/s; strong stretches cover
  ~19% of their minutes. DECISIONS #22 assumed Kaset material "can't match a
  Haghordum-only archive". The gate's outcome for Kaset-heavy channels (send to triage)
  is still safe, but the premise is wrong, and the speed sweep's exclusion of Kaset clips
  rests on it too. Revisit with the full pool numbers.
- **Shortcut accept line 4.0 → 6.2 hashes/s.** The archive audit had 1 false accept
  (4.58/s: sketch 335 placed inside another sketch's confirmed stretch of `Fyc5VWnAMog`).
  Of the audited accepts, 1 of 8 below 6.2 failed the windowed check and 0 of 42 above.
  Re-run: that span is gone, the 10 hits now in the band all confirmed, and the audit
  reads 0/50 accepted and 2/50 rejected disagreeing. The 2 rejected cases are harmless:
  a weaker second alignment of a sketch confirmed at 12.6/s on the same stretch, and a
  stretch two known duplicates (`0iKAm_aZ7Og`, `kKDydl5jRAY`) already cover.
- **Known gaps:** `2jr-BeWAfXc` and `L_YyghytxU0` (pool, 132 min) fail with "This video
  is not available" although the API says public and playable in DE.
- **For Phase S:** timelines list archive duplicates side by side on the same stretch
  (`0iKAm_aZ7Og` and `kKDydl5jRAY` in `3UZOwmPovQ4`). Merge them to one canonical before
  showing a timeline on the site.
- **Running:** pool mapping (archive then candidates index, then confirm and audit),
  restarted 00:44 with the fixes above; the 1%-step speed sweep, ~1 h left.
- **Q24:** the two 3 Sep leftovers of file 400 in `data/video` (`.part` 0 B, `.ytdl` 50 B)
  deleted by exact name; 702 of 702 videos complete. **Q25:** no global rule; the project
  learning is enough.
- **Speed sweep (01:00): speed-shifted fan copies exist.** 12 of 100 leftover `new`
  canonicals match an archive sketch after a correction: 10 at tempo x0.90, 1 at x0.95,
  1 at tape speed x0.98; 6 are Kargin Club. All three uploads that name a sketch number
  (424, 415, 402) matched exactly that sketch. DECISIONS #21 updated. Before the owner's
  triage, the `new` clusters need a speed pass (owner decision pending, Q26).
- **Owner, 01:05:** Q26 no speed pass for now (speed-shifted copies stay in the triage
  as `new`); Q27 yes, the archive self-match runs (`data/audio_index/archive_self.jsonl`);
  Q20 push the code now, the pool results in a second commit.
- **Q27, archive self-match (01:40): no other hidden duplicates.** 702 sketches matched
  against the archive in 45 min. Unknown pairs with a shared stretch >= 20 s at >= 4/s:
  16, all partial (21-34 s, 7-42% of a sketch); 13 identical audio, 3 shared music only.
  Worth a look by eye: "Kondi Tner" vs sketch 197 and "Maaaaama" vs sketch 545 (42% of
  one side each). Evidence: `data/audio_index/archive_self_pairs.csv`.

**2026-11-04, M4 fan-pool map: done** (paused 03:25 when the PC was closed, resumed 12:41
at below-normal priority, finished 14:11; the matching passes were already saved).
- **254 videos, 7,980 min:** 1,586 archive spans, 2,615 fan-clip spans, 795 `unknown`
  gaps totalling **4,252 min (53%)**.

  | Series | Videos | With archive | Minutes | Archive | Any match |
  |---|---|---|---|---|---|
  | Haghordum | 114 | 104 | 2,302 | 53% | 65% |
  | Kaset | 54 | 32 | 2,350 | 21% | 50% |
  | unclear | 82 | 20 | 3,205 | 25% | 27% |
  | Multer | 4 | 3 | 123 | 0% | 32% |

- **Kaset tapes contain archive sketches:** 79 distinct ones in 32 of 54 tapes.
  DECISIONS #22 corrected; the next gate run should drop its Kaset exception.
- **Shortcut audit:** accepted 11/50 and rejected 2/50 disagree. The 11 are not shortcut
  errors. A drift probe shows the 10 s correlation check fails on fan re-encodes (tiny
  speed drift, lossy audio, spans stretched by stray hashes) while the audio is the same
  (`_learnings/2026-11-04-1420_sample-correlation-fails-on-fan-reencodes.md`). The hits
  that check rejected cover at most 140 of the 4,252 unknown min (48 videos). Re-confirm
  those with 2 s windows before mining (M5).
- **Not Kargin, in the triage:** ՀայTV's "actors then and now" slideshows (one shared
  looping music track) came in through the gate's keep for ՀայTV and show up as `new`
  clusters of 1-3. Expect to dismiss them as out of scope.
- **Phase M5 input:** `data/compilations/timeline_pool.csv`, whose `unknown` rows are
  the stretches no archive sketch or fan clip explains. Expect speed-shifted copies among
  them too (DECISIONS #21: 12 of 100 leftover clips).
