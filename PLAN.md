# PLAN

The roadmap for the rewrite. Living document — push back, edit, reorder. Source of truth for "what comes next." Pair with `PROGRESS.md` (status) and `NOTES.md` (open questions).

## North star

**One sentence we should be able to say at the end:** "Search Kargin sketches by meaning or exact quote, jump to the moment, in Armenian."

If that sentence is wrong, every phase below changes. Confirm before building.

## Open decisions (do these in Phase 0)

- [ ] **Search unit**: episode (like old) or transcript segment (a quote with timestamp)?
- [ ] **Deployment target**: Streamlit Cloud / Hugging Face Spaces / self-hosted VM / serverless? Decides DB and infra.
- [ ] **Budget ceiling** for Gemini STT (after sampling).
- [ ] **Public or private?** Affects whether transcripts can be redistributed.
- [ ] **Languages**: Armenian only, or also romanized Armenian / Russian / English search?

Capture answers in `NOTES.md` as they're decided. Don't start Phase 1 until at least the first three are answered.

---

## Phase 0 — Spikes & decisions

Cheap, fast, just to de-risk everything below.

- [ ] **Inventory the videos**: count rows in `kargin_eng.csv`, dedupe by YouTube ID, get total duration via `yt-dlp --print duration` (no audio download needed). Output: total minutes.
- [ ] **Gemini STT spike**: pick 3 videos varying in age/quality/length. Pull audio via `yt-dlp -x`, run through Gemini audio. Manually score: are timestamps usable? Is Armenian transcription readable? Output: go/no-go on Gemini-as-primary.
- [ ] **YouTube caption check**: for the same 3 videos, fetch `yt-dlp --write-auto-subs --skip-download`. If captions exist and are decent quality, the cost calculus changes.
- [ ] **Cost estimate**: minutes × Gemini audio rate × Armenian quality factor. Compare against budget.
- [ ] **Data model sketch**: write the proposed SQL schema (tables: `episode`, `segment`, `actor`, `query_log`?) into `NOTES.md`. One page, no code yet.

Exit criteria: you can write a single paragraph answering "here's what we're building, here's the data model, here's what it costs, here's where it lives."

---

## Phase 1 — Data pipeline

Goal: a SQLite (or Parquet) database with searchable transcript segments and enriched metadata. **Two parallel tracks** since they don't share state.

### 1A — Transcripts (segments + timestamps)

- [ ] Script to download audio for each YouTube link via `yt-dlp` (cache locally, don't redownload).
- [ ] **YouTube auto-captions confirmed unusable** (see `LEARNINGS.md`): they exist for some videos but transcribe in the wrong language because the sketches open with foreign-language songs. Skip them.
- [ ] **Gemini audio is the primary path.** Prompt it to **ignore music and transcribe Armenian speech only** — Kargin intros frequently open with a Russian or Spanish song that fooled YouTube's detector and will fool a naive STT call too.
- [ ] Get word-level or sentence-level timestamps from Gemini.
- [ ] Write segments to DB with: `episode_id`, `start_sec`, `end_sec`, `text`, `source` (gemini), and ideally `kind` (speech / song / silence) so downstream search can filter or weight.
- [ ] Idempotent: re-running skips already-processed videos. **Loud failure on errors** — never silently skip a video.
- [ ] Use `logging` (not `print`), log to file + console.

### 1B — Metadata enrichment

- [ ] For columns the original CSV has (`location`, `main_actors_count`, `lighting`, `roles_names`, `languages`): figure out which are reliable as-is, which need backfilling.
- [ ] Use multimodal AI (Gemini Vision on a few thumbnails/frames) for visual columns: location type, lighting, rough actor count.
- [ ] Use the transcript itself for textual columns: actor names mentioned, language detection.
- [ ] Keep the original hand-curated values where they exist. Don't overwrite human-curated data with AI-curated data without flagging — track `source` per field.

Exit criteria: a single SQLite file (or Parquet set) with episodes, segments, and enriched metadata that you'd be willing to ship.

---

## Phase 2 — Search module

**One module, used by every surface.** No duplication like the old project.

- [ ] **Exact search**: SQLite FTS5 over segment text. Sub-100ms on the full dataset.
- [ ] **Semantic search**: pick an embedding model that handles Armenian (multilingual-e5, Cohere multilingual, or Gemini embeddings). Store embeddings in the same DB (sqlite-vec) or Parquet+FAISS. No separate vector DB unless deployment forces it.
- [ ] **Skip "fuzzy"** as a separate mode. FTS5 handles typos via prefix matching; semantic handles meaning. Fuzzywuzzy on Armenian is a tarpit.
- [ ] **Filters**: location, language, actor count, episode, time range — composable with both search modes.
- [ ] Public API surface: `search(query, mode="auto"|"exact"|"semantic", filters={}, limit=N) -> list[Segment]`. Single function, well-typed.
- [ ] Tests against a frozen set of expected results (golden file) so refactors don't silently break ranking.

Exit criteria: one Python module, one CLI entry point (`python -m kargin.search "query"`), and tests.

---

## Phase 3 — Web UI

- [ ] Pick framework: Streamlit (fastest, ugly), Gradio (similar), or a real web app (Next.js/SvelteKit + FastAPI). Default to Streamlit unless deployment demands otherwise.
- [ ] One main search page. Results show episode, timestamp, snippet, link to YouTube at the timestamp (`&t=Ns` syntax).
- [ ] Filters in sidebar: location, actor count, language.
- [ ] Mode toggle: exact vs semantic.
- [ ] **Log every search** to `query_log` table from day one — don't bolt on later.
- [ ] Don't bypass the entry point this time: make a clean entrypoint that doesn't depend on Streamlit's session-state-as-database trick.

Exit criteria: a stranger can find a quote and click straight to the YouTube moment.

---

## Phase 4 — Telegram bot

- [ ] Use the same search module from Phase 2. Zero duplicated logic.
- [ ] Same commands as old bot are fine; just don't reimplement the search inside the handler.
- [ ] Token via env var, dotenv for local.
- [ ] Logs to the same `query_log` table.

Exit criteria: bot works, and changing search behavior in one place changes both surfaces.

---

## Phase 5 — Polish

Things from the old app worth keeping:

- [ ] Random episode page.
- [ ] EDA / stats page (episodes per location, top actors, etc.).
- [ ] Info / links page.
- [ ] (Maybe) "popular searches" derived from `query_log`.

## Future ideas (not now)

Captured here so they're not lost; not in scope for the current build.

- **Song extraction per video.** Detect and isolate musical segments (intros, outros, in-sketch songs). Tooling options: `pyannote-audio` for music-vs-speech segmentation, Demucs / Spleeter for source separation if isolating vocals from background, or a Gemini-audio prompt classifying segments. Output: a `songs` table with `episode_id`, `start_sec`, `end_sec`, optional `title`/`lyrics`. Useful for a "songs only" filter or a soundtrack page.
  - **Note**: this overlaps with Phase 1A. Music-vs-speech segmentation is preprocessing the STT pipeline already needs (intros are foreign-language songs that mislead Armenian transcription). If we add a `kind` column to segments in Phase 1A, the dedicated "songs" feature becomes a simple `WHERE kind = 'song'` query later — no separate pipeline needed.
- See `NOTES.md` for additional ideas.

---

## Explicitly out of scope

- User accounts, favorites, watch history.
- Mobile app.
- Multi-language UI (English, Russian) — search may be multilingual, UI stays Armenian + minimal English.
- Any auth or rate limiting unless deployment demands it.
- A REST API for third parties — this is a personal project until proven otherwise.

## Risks to watch

- **Gemini STT quality on Armenian comedy with overlapping voices** could be poor. Phase 0 spike de-risks this.
- **Cost overrun** on STT — set a hard cap before running batch.
- **YouTube ToS** for bulk audio downloads. Personal/research use is generally tolerated; public hosting of derived transcripts is murkier.
- **Embedding model choice for Armenian** is non-obvious. Test recall on a few hand-built query/expected-segment pairs before committing.
