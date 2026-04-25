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

This is an **old project being recreated with significant changes**. The original 2-hour vibecoded version has been moved to `old/` for reference. The root is intentionally near-empty so the rewrite can start clean.

Repo layout right now:

```
.
├── CLAUDE.md, PLAN.md, PROGRESS.md, LEARNINGS.md, NOTES.md   # project memory
├── kargin_eng.csv                                            # source-of-truth curation data, 702 rows
├── data/
│   ├── youtube_metadata.csv                                  # 702 rows, fetched via YouTube Data API v3
│   ├── audio/                                                # gitignored, 702 webm/opus, 1.6 GB
│   ├── video/                                                # gitignored, 360p smoke-test only so far
│   ├── transcripts_raw/                                      # gitignored, yt-dlp JSON3 + .no_captions sentinels
│   └── transcripts/                                          # gitignored, simplified per-video JSON
├── scripts/
│   ├── fetch_youtube_metadata_api.py                         # YouTube Data API v3, the working metadata fetcher
│   ├── fetch_youtube_metadata.py                             # yt-dlp version, kept for reference (rate-limit issues)
│   ├── download_audio.py                                     # bulk audio downloader
│   ├── download_video.py                                     # bulk video downloader, 360p
│   ├── fetch_transcripts.py                                  # YouTube source-lang captions via yt-dlp
│   └── convert_transcripts.py                                # JSON3 → simplified per-video JSON
├── pyproject.toml, uv.lock                                   # uv-managed deps
├── .env.example                                              # template; real .env is gitignored
├── internal/                                                 # gitignored — user-local curation files
└── old/                                                      # the original codebase, frozen
```

Direction for the rewrite is captured in `NOTES.md`. Until that's decided, **don't pattern-match off `old/`** — the rewrite is not a refactor of it, and copying its choices forward (CSV-only, fuzzywuzzy row-scan search, dual duplicated surfaces) is probably wrong.

## Environment

Project uses `uv` with a `pyproject.toml` and a local `.venv/`. Don't use system Python directly.

```bash
uv venv          # one-time
uv sync          # install / update deps from pyproject.toml
uv add <pkg>     # add a new dep
uv run python scripts/<x>.py    # run a script in the venv
```

Deps are intentionally minimal at the start of the rewrite — add only what you need.

## The data: `kargin_eng.csv`

The one artifact that survives from the old project. Columns:

`titles, links, text_common, text, main_actors, main_actors_count, roles_names, location, lighting, languages, done`

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
