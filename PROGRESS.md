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

## In progress
- Phase 0 of `PLAN.md`: metadata complete. Next sub-step is the Gemini STT spike (3-5 representative videos).

## Next
- **Gemini STT spike**: pick 3-5 videos varying in length/era, download audio via `yt-dlp -x`, run through Gemini audio with a prompt that says "ignore music, transcribe Armenian speech only." Score the output for Armenian readability and timestamp usability.
- Pick model for the spike: start with Gemini 2.0 Flash (cheapest, ~$3 for whole archive). If quality is bad, escalate to 2.5 Pro (~$30).
- Confirm/adjust the data-model decision in `PLAN.md` open decisions (segment vs episode unit) based on what timestamps Gemini returns.
- Resolve remaining `PLAN.md` open decisions (deployment target, public/private, languages) before kicking off Phase 1.
