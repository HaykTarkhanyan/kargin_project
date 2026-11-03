# Extending the archive beyond the 702 sketches

Plan, written 2026-11-03, revised the same day to cover compilations, then reviewed
against the code (findings and what changed: section 15). **Nothing here has been
run yet.** This file is the full record: every finding, number and
open decision lives here, not in the chat. Answer decisions by their ID (`Q5: b`).

Inputs: the channel scout (`data/channel_scout/`, DECISIONS #18), a read of every
pipeline script's docstring and of the build, review and annotation code,
LEARNINGS.md, DECISIONS.md, HANDOFF.md, and the measurements quoted below.

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
   (LEARNINGS 2026-08-01). The current check is a fingerprint shortlist plus
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
| Standalone sketch on KarginTV, not in the archive | KarginTV | 6 Haghordum (175, 176, 177, 194, 195, Bufet) + 8 Multer in scope; the 100 Sketch Show uploads are out (Q5) | Phase A with matching (KarginTV re-uploads its own sketches: all 23 duplicate pairs in the archive are KarginTV vs KarginTV), then Phase B |
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
- yt-dlp at its current release AND deno installed (LEARNINGS 2026-09-03: without both, formats 403 or vanish).
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
3. Compare video and audio stream durations with ffprobe on the new files; more than 2 s apart is a truncated download (LEARNINGS 2026-09-03). This needs a small probe script; none exists.

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
   - `scripts/split_batch_transcript.py --captions <file>`. Its duration check must pass (LEARNINGS 2026-08-02).

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
- `uv run python scripts/embed_annotations.py --force` (a full rebuild, about $0.03). Keep its one-vector-per-call assertion (LEARNINGS 2026-09-07).
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
| S2 | Build: **new** `scripts/kargin_build/compilations.py` folds the timeline into `sketches.json`. A compilation carries `kind` and `contains: [{id, startSec}]`; a sketch inside one carries `alsoIn: [{id, startSec}]`. It fails loudly on an id that isn't a sketch (same rule as `neighbors.py`) |
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
| Gemini text annotations | ~$0.002 / sketch | LEARNINGS 2026-09-07 (A/B on flash3, thinking off) |
| Embeddings, full rebuild | ~$0.03 | probe cost ~$0.0001 per 3 docs |
| YouTube Data API, Shazam, audfprint | $0 | free quota, free tools |
| Data API quota | B2 ~10 units, B0 probe ~15, B20 ~20 per run (~200 with the scout re-check), out of 10,000/day | 1 unit per 50 videos |
| Disk, everything at once | ~8.5 GB of the 16 GB free (A3 + M3 + ~300 sketches) | sum of the rows below; see Q9 |
| Visual annotation | ~11k Claude tokens / sheet + Opus for ~14% | LEARNINGS 2026-09-03/04 |
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

From LEARNINGS, HANDOFF and this session:

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
