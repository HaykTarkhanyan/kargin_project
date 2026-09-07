# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Read these first

These three files carry the live state of the project. Read them at the start of every session and update them as work progresses:

- **[PLAN.md](PLAN.md)** — the roadmap. Phases, decisions, exit criteria. Source of truth for "what comes next."
- **[PROGRESS.md](PROGRESS.md)** — what's done, in progress, and next. Update when starting/finishing work so future sessions can pick up cleanly.
- **[LEARNINGS.md](LEARNINGS.md)** — append-only log of non-obvious lessons, gotchas, and decisions. Add entries when you discover something that isn't visible in the code itself.
- **[NOTES.md](NOTES.md)** — open questions, ideas, and free-form context for the rewrite. Edit freely.

## Working norms (project-specific)

The four general behavioral rules live in the global `~/.claude/CLAUDE.md`. Project-specific additions:

- **This is a rewrite, not a refactor.** Don't copy patterns from `old/`. The point is to do it differently. When tempted to lift code, write fresh and only consult `old/` for *what existed*, not *how it was built*.
- **For non-trivial changes, plan first.** A two-minute plan saves twenty minutes of rework. Use plan mode or write the plan to `PROGRESS.md`'s "In progress" section before touching code.
- **Confine scope to the task.** If the user asks for X, do X. Surface "while we're here, also Y?" as a question, not a unilateral edit.
- **Heavy exploration goes to a subagent.** Don't pollute the main context with grep walks across `old/` or unrelated codebases. Delegate, get a summary, keep the main context clean.
- **Use `@file` references when pointing to examples.** "Implement X following the pattern in `@scripts/fetch_youtube_metadata_api.py`" is much better than describing the pattern from memory.
- **Reach for Context7 before guessing library APIs.** When working with any external library or framework (yt-dlp, pandas, Streamlit, the YouTube Data API, embedding models, etc.), use the Context7 MCP to fetch live docs rather than relying on training-data memory of syntax. Especially important for fast-moving libraries (yt-dlp options drift, ML SDKs change versions often). Skip Context7 only for general programming concepts or for code we already wrote in this repo.

## Current state

This is an **old project recreated with significant changes**. The original 2-hour vibecoded version lives frozen in `old/`. The rewrite is now well underway: the data pipeline has run end to end over the 702 sketches, and two user-facing surfaces exist — a live TypeScript Telegram bot (`bot/`) and a Next.js site backed by Firestore (`web/`).

Repo layout (counts as of 2026-09; media dirs under `data/` are gitignored):

```
.
├── CLAUDE.md, PLAN.md, PROGRESS.md, LEARNINGS.md, NOTES.md, DECISIONS.md, DEFERRED_TODO.md
├── kargin_eng.csv                  # source-of-truth curation data, 702 rows
├── data/
│   ├── youtube_metadata.csv        # 702 rows, YouTube Data API v3
│   ├── audio/                      # 702 webm/opus, 1.6 GB
│   ├── video/                      # full mp4 per sketch, named NNN_Title_<video_id>.mp4
│   ├── contact_sheets/             # frame-grid image per video (input to annotate-sheets skill)
│   ├── visual_annotations/         # 702 JSONs — visual annotation sweep is complete
│   ├── transcripts_raw/            # yt-dlp JSON3 + .no_captions sentinels
│   ├── transcripts/                # 484 simplified per-video JSONs (rest have no captions)
│   ├── transcripts_gemini/         # small flash-lite vs pro STT pilot (18 files), not a full run
│   ├── transcription_batch/        # batched-SRT transcription experiment
│   ├── audio_fingerprints.npz, song_matches.csv, music_credits.csv   # music-recognition pass
│   ├── duplicates.csv              # 32 detected duplicate pairs
│   └── corrections.csv, backups/   # review corrections (empty now) + timestamped snapshots
├── scripts/                        # Python pipeline: fetch, download, transcribe, fingerprint, dedupe, review UI
├── bot/                            # TypeScript Telegram bot (live), Dockerfile
├── web/                            # Next.js site + Firestore — has its own CLAUDE.md, read it before touching web/
├── experiments/, docs/, tests/, _knowledge/, _work_sessions/
├── pyproject.toml, uv.lock         # uv-managed Python deps
├── .env.example                    # template; real .env is gitignored
├── internal/                       # gitignored — user-local curation files
└── old/                            # the original codebase, frozen
```

**Don't pattern-match off `old/`** — the rewrite is not a refactor of it, and copying its choices forward (CSV-only, fuzzywuzzy row-scan search, dual duplicated surfaces) is wrong. Decisions made along the way live in `DECISIONS.md`.

## Environment

Project uses `uv` with a `pyproject.toml` and a local `.venv/`. Don't use system Python directly.

```bash
uv venv          # one-time
uv sync          # install / update deps from pyproject.toml
uv add <pkg>     # add a new dep
uv run python scripts/<x>.py    # run a script in the venv
```

Add deps only when needed, pinned exact (`==`).

Gemini runs via **Vertex AI** on the $300 GCP credits: three `GOOGLE_*` vars in `.env` (see `.env.example`), auth via machine-wide gcloud ADC — there is no key file to copy. The separate `GEMINI_API_KEY` in `.env` is an AI Studio key and does **not** use the credits; with `GOOGLE_GENAI_USE_VERTEXAI=true` set, `genai.Client()` routes through Vertex.

`bot/` and `web/` are Node projects with their own `package.json` — `npm` there, not uv.

## The data: `kargin_eng.csv`

The one artifact that survives from the old project, extended during the rewrite. Columns:

`id, titles, links, text_common, text, main_actors, main_actors_count, roles_names, location, lighting, languages, done, video_id, duplicate_of, status_final`

- `id`, `video_id`, `duplicate_of`, `status_final` were added by the rewrite pipeline (`scripts/add_status_final.py`, dedupe). `status_final` is currently `False` for all 702 rows — no row has been finalized yet.

- `links` are YouTube URLs (mix of `youtube.com/watch?v=...` and `youtu.be/...`, sometimes with `&list=` and `&t=` params).
- `text` is Armenian dialogue, hand-curated, often partial.
- `text_common` holds catchphrases / common expressions.
- `main_actors_count` is a string in the CSV; old code coerces to numeric with NaN → 0.

## Reference: what `old/` contains

The frozen original. See `old/README.md` for its self-description. High-level:

- `old/Home.py` + `old/pages/` — Streamlit multipage app. `Home.py` was the required entry point; pages depended on `st.session_state` populated there.
- `old/telegram_bot.py` — standalone Telegram bot (`@KarginSearchBot`), independently loaded the same CSV.
- `old/youtube_utils.py` — dynamic-import wrapper around `pytubefix` so the app degrades cleanly when it's missing.
- Two surfaces, no shared search module — fuzzywuzzy logic was duplicated. See `LEARNINGS.md` for known bugs and gotchas before lifting any of it forward.

If the rewrite ever needs to run the old app for comparison, install via `old/requirements.txt` and run from inside `old/` (paths in those scripts assume the CSV is in the working directory — copy or symlink `kargin_eng.csv` in).
