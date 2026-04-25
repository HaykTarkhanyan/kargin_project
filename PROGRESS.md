# PROGRESS

Tracks what's done, in progress, and next. Update as work happens.

## Status
Pre-rewrite. The existing codebase is the original 2-hour vibecoded version (Streamlit + Telegram bot over a static CSV with fuzzywuzzy search). A significant recreation is planned but not yet started.

## Done
- 2026-04-25: Audited existing project, created `CLAUDE.md`, `PROGRESS.md`, `LEARNINGS.md`, `NOTES.md` scaffolding for the recreation.
- 2026-04-25: Moved the original codebase into `old/` via `git mv` (history preserved as renames). Root now holds only the four memory files plus `kargin_eng.csv`.
- 2026-04-25: Wrote `PLAN.md` with phased roadmap (open decisions → data pipeline → search → UI → bot → polish). Added "song extraction" to future-ideas section.
- 2026-04-25: Built `scripts/fetch_youtube_metadata.py` — yt-dlp-backed metadata fetcher, idempotent, schema in `data/youtube_metadata.csv`. Smoke-tested on 3/695 videos. See `LEARNINGS.md` for findings (YouTube auto-captions transcribe Armenian as Russian/Spanish, so they're unusable).
- 2026-04-25: Set up `pyproject.toml` and `uv` venv (Python 3.11.13). Made the yt-dlp script parallel (ThreadPoolExecutor, 8 workers). Hit YouTube anti-bot rate-limiting at ~150 requests; cookies workaround blocked by Chromium DB lock.
- 2026-04-25: Switched to YouTube Data API v3 (`scripts/fetch_youtube_metadata_api.py`). Whole archive metadata fetched in ~1 sec across 14 batched calls. Result: **695 rows, 0 failures, 33.55 hours total audio, all but 1 video public, zero usable captions.** Cost estimate for Gemini STT: $3-30 depending on model — Phase 0's "is this affordable" question is settled.
- 2026-04-25: Cross-referenced `internal/` curation files (3 spreadsheets, 600 unique video_ids). Found 6 videos missing from `kargin_eng.csv` — all alive on YouTube. Added the 6 to `kargin_eng.csv` (2 with hand-curated phrases from internal, 4 with title+link only). Refetched their API metadata. **All three data sources now consistent: kargin_eng.csv has 702 rows / 701 unique IDs, data/youtube_metadata.csv has 701 rows / 701 unique IDs, internal/ ⊂ both.** EDA notes: archive is 1 channel (KarginTV), 1 language (`hy` for 700/701), 33.6 hours total, 488M cumulative views, sketch numbering 75-702 with ~40 gaps.
- 2026-04-25: Initial commit of the rewrite scaffolding at `9e8708b` ("Reset for rewrite: archive old code, add planning + data pipeline scaffolding"). 31 files changed, 18 renames into `old/`. Working tree clean. Branch is 1 commit ahead of `origin/main`, not pushed.
- 2026-04-25: Karpathy's four behavioral rules (Think Before Coding / Simplicity First / Surgical Changes / Goal-Driven Execution) added to global `~/.claude/CLAUDE.md`. Project CLAUDE.md keeps only the project-specific addenda (rewrite-not-refactor, plan-first, scope discipline, subagent for exploration, `@file` references).
- 2026-04-26: Filled the missing YouTube link for sketch 672 (`hp0U2719O0A`, 176s, public, `hy`, uploaded 2013-04-11) — the one row that was curated but unlinked. Refetched its metadata via the API (resume logic skipped the other 701). **Both CSVs now: 702 rows, 702 unique video_ids, zero duplicates, zero diff between the two id sets.**
- 2026-04-26: Wrote `scripts/download_audio.py` — single-threaded, no-cookies, resume-by-file-presence audio downloader using `yt-dlp` `bestaudio/best`. Detects YouTube's bot-detection error and stops early. `data/audio/` and `data/video/` added to `.gitignore`. Smoke test on 1 video returned a 2.8 MB webm/opus file at ~111 kbps. Ready for a full run; expect to hit the rate-limit wall around ~150 videos and need multiple sessions to finish all 702.
- 2026-04-26: Project `CLAUDE.md` updated with a Context7 reminder (use the MCP to fetch live docs when touching external libraries, instead of trusting training-data syntax). Stale "701 rows" reference in CLAUDE.md repo layout corrected to 702.
- 2026-04-26: Renamed audio downloads to `{seq:03d}_{title}_{video_id}.{ext}` format (sequential seq from metadata.csv row order — sketch numbers are not unique enough to use as id: 4 dupes among 598, 104 titles lack the pattern). Resume regex anchors to the 11-char id before the extension, so it works across naming schemes. Single-video 360p experiment landed 8.32 MB in 7.3 s for a 201-sec sketch (format 18, pre-merged mp4). Extrapolation: full archive at 360p ≈ 4.7 GB; audio-only ≈ 1.6 GB.
- 2026-04-26: Wrote `scripts/download_video.py` as a parallel of the audio downloader (same naming, same resume, same rate-limit auto-stop) targeting `best[height<=360]/best`. Output goes to `data/video/` (gitignored). Not run in bulk yet.
- 2026-04-26: Full-archive audio download completed in **one run, no rate-limit wall**: 702/702 videos, 0 failures, 1.6 GB total, 44:54 wall time, ~3.84 sec/video. Cookieless, single-threaded. Files in `data/audio/{seq:03d}_{title}_{video_id}.{ext}` format, mostly webm/opus at 100-135 kbps. Updated LEARNINGS.md — the previously documented "~150-request wall" was specifically a parallel-fetch artifact; serial yt-dlp does not trigger it at archive scale.

## In progress
- Phase 0 of `PLAN.md`: metadata complete. Next sub-step is the Gemini STT spike (3-5 representative videos).

## Next
- **Gemini STT spike**: pick 3-5 videos varying in length/era, download audio via `yt-dlp -x`, run through Gemini audio with a prompt that says "ignore music, transcribe Armenian speech only." Score the output for Armenian readability and timestamp usability.
- Pick model for the spike: start with Gemini 2.0 Flash (cheapest, ~$3 for whole archive). If quality is bad, escalate to 2.5 Pro (~$30).
- Confirm/adjust the data-model decision in `PLAN.md` open decisions (segment vs episode unit) based on what timestamps Gemini returns.
- Resolve remaining `PLAN.md` open decisions (deployment target, public/private, languages) before kicking off Phase 1.
