# NOTES

Open questions, ideas, and free-form context for the project.

## About the recreation

The plan is to rebuild the Kargin search project with significant changes. Direction is not yet decided. Capturing context here as it emerges.

## Open questions

- What's the intended primary surface? (web app, Telegram bot, both, something new like a Discord bot or mobile app)
- Search approach: keep fuzzy string matching, move to full-text search (SQLite FTS5, Meilisearch), or embeddings/semantic search?
- Where does `kargin_eng.csv` come from originally? Is there a pipeline that produces it, or was it hand-curated? Does it need updating?
- Will the rewrite include subtitle / transcript extraction from the YouTube videos? (Could replace the manually-curated `text` column.)
- Hosting: stay on Streamlit Cloud, move to a real backend (FastAPI + frontend), or something else?
- Multi-language plan: keep Armenian-first, add Russian/English search, romanization?

## Reference: what the original does

- Two surfaces (Streamlit, Telegram) over one CSV
- Fuzzywuzzy search across `text`, `text_common`, `titles`, `main_actors`, `roles_names`
- Optional YouTube metadata via `pytubefix`, gated by a session-state toggle
- No DB, no auth, no API, no users, no caching beyond Streamlit session state

## Ideas worth weighing

- Single shared search module instead of duplicating the algorithm in each surface.
- Move data to SQLite (or Parquet) so updates and indexing are cleaner.
- Add `youtube_id` as a real column instead of parsing it on every page load.
- Consider a thin REST/GraphQL API so future surfaces don't keep reimplementing search.
