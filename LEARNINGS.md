# LEARNINGS

Non-obvious lessons, gotchas, and decisions discovered during work. Append-only — things not derivable from the code itself.

## From the original (pre-rewrite) codebase

- **`pytubefix` scrapes likes via a deeply nested path** (`yt.initial_data['videoPrimaryInfoRenderer']...`). This breaks whenever YouTube changes its page structure. Any rewrite that depends on like counts needs a more durable source (official API or accept-it-might-be-missing).
- **YouTube thumbnails do NOT need pytubefix or any API** — `https://img.youtube.com/vi/<VIDEO_ID>/mqdefault.jpg` works directly. Useful fallback when avoiding YouTube API dependencies.
- **Streamlit multipage apps have no enforced entry point** — users can navigate directly to `pages/X.py`. The original handles this by checking `'df' in st.session_state` and erroring out. Worth designing around in the rewrite.
- **`fuzzywuzzy` is slow on row-by-row scans** — the Telegram bot iterates the entire DataFrame for every text search. Fine at a few hundred rows; would not scale.
- **Bug at `old/pages/1_Search_Episodes.py:349`**: `is_fuzzy=(search_type == "Fuzzy Search")` — but radio values are `"Simple Fuzzy"`/`"Advanced Fuzzy"`, so highlight always falls through to exact-match branch. Fuzzy highlights never render.

## From the metadata-fetch (2026-04-25)

- **Input has 695 unique YouTube video_ids** in `kargin_eng.csv` (`links` column). Zero unparsable URLs in the smoke test.
- **`yt-dlp` is the right tool**, not pytubefix. ~2 sec per video for metadata-only, no audio download.
- **YouTube hid public dislike counts in Dec 2021.** `dislike_count` is `null` for ~all videos. Keep the column for completeness; don't expect data.
- **YouTube's `language` field is unreliable for Armenian content.** Auto-detection often labels Kargin sketches as Russian or Spanish. Don't trust it; use it only as a hint.
- **YouTube's `automatic_captions` dict mostly contains auto-translations, not source captions.** The single key ending in `-orig` (e.g. `ru-orig`) marks the language YouTube actually transcribed in. Everything else is derived. Parse `-orig` to get `auto_caption_source_lang`.
- **For Kargin videos specifically, YouTube auto-captions are useless even when they exist** because they're transcribed in the wrong language. Smoke sample (n=3): 2 had auto-captions in `ru` and `es`, 1 had none. Implication: **Gemini STT is the primary transcription path for essentially all videos**, not a fallback.
- **Why YouTube misclassifies the language: Kargin sketches frequently open with a Russian or Spanish song as the soundtrack** (per project owner). YouTube's language detector locks onto the song lyrics in the first few seconds and labels the whole video accordingly, even though the dialogue is Armenian. Two consequences for the transcription pipeline:
  1. Gemini STT will likely hit the same failure mode if fed full audio. Either prompt it to focus on speech and transcribe Armenian specifically, or segment out music first.
  2. The `auto_caption_source_lang` column is therefore an indirect signal of "what song is in the intro," not "what language the video is in." Could be useful for a soundtrack-detection feature but is not a reliable language label.
- **No manual captions on any of the smoke-tested videos.** Likely true for the whole set — these are old user uploads.
- **No YouTube chapters either.** Don't expect free segment data from there.
- **Pandas reads empty CSV cells as `NaN`, not `""`.** Caught this in `load_resume()`: `r.get("fetch_error") or ""` evaluated to `NaN`, then `str(NaN)` is `"nan"` (truthy), so the resume logic considered every prior row failed and refetched everything. Always check `pd.isna(value)` explicitly when distinguishing "no error" from "error string". Or use `pd.read_csv(..., keep_default_na=False)` if you want all empties as `""`, but that complicates numeric columns.

## Concurrency & infra (2026-04-25)

- **yt-dlp metadata fetches parallelize cleanly with threads.** I/O-bound, ~2s wall time per call serial → ~0.25s effective with 8 workers. ThreadPoolExecutor + per-call `yt_dlp.YoutubeDL(...)` instances (don't share an instance across threads). 8 workers is fine; haven't tested higher.
- **`uv venv` picked Python 3.11.13 over the system 3.10.10** when `requires-python = ">=3.10"` is set. uv prefers newer Pythons it has access to. Pin a specific minor if reproducibility matters.
- **YouTube rate-limits cookie-less yt-dlp around ~150 sequential requests.** First batch went fine, then YouTube returned `"Sign in to confirm you're not a bot"` for everything afterwards. Once it kicks in, every request fails fast (~200ms) until cookies are provided. Fix: `cookiesfrombrowser=("firefox",)` in yt-dlp opts (or `--cookies-from-browser firefox` on the CLI). uv-managed yt-dlp can read cookies from any major browser; you don't need to be logged in heavily, just have a recent session. Plan around this for any bulk operation.
- **Chromium-based browsers (Chrome, Edge, Brave) lock their cookie DB while running on Windows** — yt-dlp errors with `"Could not copy Chrome cookie database"` (issue #7271). Workarounds: (a) close all Chrome windows briefly, (b) use Firefox, which doesn't lock, or (c) export cookies via a browser extension and use `--cookies <file>` instead.
- **`taskkill /F /PID ... /T` from Git Bash** mangles the `/F` flag because Git Bash's MSYS path translation interprets it as a Unix path (`F:/`). Wrap in `cmd //c "taskkill /F /PID ..."` to bypass translation.
- **The resume logic gets validated by failure**: a 130-success / 565-fail run was the perfect test for the NaN-handling fix in `load_resume()`. After the fix, restart correctly identified 130 successes and only retried the 565 failures. This is the kind of property you can't unit-test as cheaply as you can validate against real partial-completion state.

## YouTube Data API v3 vs yt-dlp (2026-04-25)

- **API key flow worked first try.** Console signup → enable YouTube Data API v3 → create API key → paste in `.env` as `YOUTUBE_DATA_API_KEY`. Project hits the API as 14 batched calls of 50 video IDs each, ~0.5 sec total wall time vs 25+ minutes for yt-dlp.
- **API is dramatically more reliable than yt-dlp** for bulk metadata: no cookies, no rate-limit anti-bot, batches up to 50 ids per call. Cost: 1 quota unit per `videos.list` call regardless of batch size, so 695 videos = 14 units (free quota is 10,000/day).
- **`yt_declared_language` from the API is much better than yt-dlp's `language` field.** API returns the uploader-declared language (`hy` for Armenian on 578/695 Kargin videos); yt-dlp's auto-detection got fooled by foreign-language song intros and returned `ru`/`es`. The API is the right source for "what language is this video supposed to be in."
- **`captions.list` API costs 50 units per video** (vs 1 for `videos.list`). For 695 videos that's 34,750 units, 3.5x daily quota. Skip it — for this project we already established auto-captions are unusable, and the cheap `contentDetails.caption` boolean ("does any caption exist?") is enough.

## Archive shape (2026-04-25)

- **695 unique videos, 33.55 hours total runtime.** Median sketch length 2:37, mean 2:54, range 30 sec to 19:37.
- **Upload window: 2012-06-15 to 2013-04-11** — only ~10 months of activity. Looks like a single season/run of the show, not the entire history of Kargin Haghordum. May or may not matter for the rewrite scope.
- **488M cumulative views**, dominated by KarginTV channel.
- **All but 1 video are public.**
- **Zero videos with usable captions.** Gemini STT will handle 100% of transcription work.
- **Estimated Gemini STT cost for the whole archive: $3-30** depending on model (Flash vs Pro). The cost concern in `PLAN.md` Phase 0 was overblown.
