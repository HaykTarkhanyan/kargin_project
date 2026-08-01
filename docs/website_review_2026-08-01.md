# Website review + idea backlog (2026-08-01)

Full codebase review of `web/` plus a data-asset inventory, done on branch `feat/website-v2`.
Method: two read-only exploration passes (code review of app/components/lib; inventory of what
data exists vs what the site uses) plus inline reading of the key files. Nothing was changed.

Verdict: the codebase is in good shape - lean deps (just Fuse.js), memoized search, watch pages
are server components (build-time rendering, no dataset leak), CI gates on pytest + eslint + tsc +
vitest. The two big holes: **zero SEO infrastructure** on a 700-page content archive, and **the
full 1.6 MB dataset still ships inside client JS** on the most-visited pages. Separately, a lot of
existing data never reaches the site (see inventory below).

---

## A. Improvements, prioritized

### A1. SEO package (highest value per hour on the whole list)

The site is essentially invisible to search engines beyond the homepage. Confirmed absent:

- No `generateMetadata` anywhere in `web/app/` - all 702 sketch pages inherit the one generic
  title/description from `web/app/layout.tsx:10-13`.
- No `app/sitemap.ts`, no `app/robots.ts`.
- No OpenGraph / Twitter tags, no JSON-LD anywhere (grep for `openGraph|application/ld+json`
  returns nothing).
- No `metadataBase` in `layout.tsx` - required because of `basePath: "/kargin_project"`
  (`web/next.config.ts:12`), otherwise canonical/OG URLs resolve wrong.
- The watch page (`web/components/WatchView.tsx`) renders **no h1 / no visible sketch title at all**.

Everything needed is already in the `Sketch` type (`web/lib/types.ts`): `title`, `text`,
`textCommon`, `thumbnail`, `uploadDate`, `durationSec`, `viewCount`, `url`. So this is a
build-time-only change:

1. `generateMetadata` in `web/app/sketch/[id]/page.tsx`: unique title (sketch title + quote),
   description from `textCommon`/`text` snippet, canonical.
2. `metadataBase` in `layout.tsx`.
3. OG + Twitter card tags using the YouTube thumbnail (`i.ytimg.com` - external images are fine
   in meta tags on static export).
4. `VideoObject` JSON-LD per sketch page (thumbnail, uploadDate, duration, embedUrl).
5. `app/sitemap.ts` + `app/robots.ts` (both work with `output: "export"`).
6. Add an h1 with the sketch title to `WatchView`.
7. Same treatment for `/actor/[name]` pages (13 pages).

Bonus beyond Google: OG tags make links shared in Telegram/WhatsApp show the thumbnail + quote -
big for this audience.

### A2. Stop bundling 1.6 MB of JSON into client JS

`web/lib/data.ts:2` statically imports `public/data/sketches.json`. Any `"use client"` component
that touches `ALL` gets the whole array inlined into its JS chunk. Affected routes:

- Home: `web/components/SearchExperience.tsx:4`
- `web/app/find-my-name/page.tsx:5`
- `web/app/random/page.tsx:4` - the absurd case: ships the entire archive to pick one random id.
  A build-generated id list (or precomputed random redirect data) cuts this route ~99%.

Fix direction: fetch `sketches.json` at runtime in the client (it then caches independently of JS
and is shared across pages), or split a slim search index from full records. Note the server
components (sketch pages, soundboard) already use the build-time path correctly - don't touch those.

### A3. Dark theme contrast bug on primary CTAs (a11y, user-visible)

In dark mode `--ink` flips to `#F2F2F5` (`web/app/globals.css:26`) while `--orange` stays
`#F2A800` -> ~1.7:1 contrast, near-unreadable light-on-orange. Affected:

- "Բեռնել ևս" button `web/components/SearchExperience.tsx:72`
- "Դիտել YouTube-ում" `web/components/WatchView.tsx:19`
- Quiz buttons `web/components/QuizGame.tsx:71,140`

Fix: force dark text on orange surfaces (e.g. a `text-on-accent` token that stays dark in both themes).

Also: `--muted: #8A7C64` on `--paper: #FBF3E2` is ~3.7:1 in light mode (below AA 4.5:1) and is
used for the smallest 10-12px text everywhere (SketchCard, Hero, RelatedList, stat labels).

### A4. Lite YouTube embed on watch pages (perf)

`WatchView.tsx:14` loads the YouTube iframe eagerly on all 702 pages (~1 MB+ of third-party JS
before the user decides to play). Render thumbnail + play button, swap in the iframe on click
("lite embed" pattern). Also consider `youtube-nocookie.com`.

### A5. Smaller correctness / UX fixes

- **Logging mode is wrong**: `SearchExperience.tsx:42` always logs `mode: "exact"`, even for
  fuzzy-only hits. Have `searchSketches` report whether fuzzy contributed, or log the gate state.
- **Query not in URL**: filters seed FROM `?location=`/`?actor=` but nothing writes back; a search
  isn't shareable and dies on refresh/back. Sync `q` (+ filters) via `replaceState`.
- **No `app/not-found.tsx`**: bad sketch/actor URLs dead-end on Next's bare 404 with no site nav.
- **findName snippet gap**: `web/lib/findName.ts` matches over `text + textCommon` (line ~42) but
  `snippetOf` (line ~26) only scans `textLines(sketch.text)` - a name matched only via `textCommon`
  shows a generic fallback instead of the matching line.
- **find-my-name reinvents the card**: `web/app/find-my-name/page.tsx:53-64` duplicates SketchCard
  markup and renders the thumbnail as CSS `background-image` (no alt, not lazy). Reuse
  `components/SketchCard.tsx`.
- **Hardcoded dataset facts drift**: `app/stats/page.tsx:12,17` ("702", "10 ամիս", "~76%"),
  `lib/quizzes.ts` (702/602/counts), `app/about/page.tsx` (702/602). Derive from `STATS`/`ALL`
  at build so they can't go stale.
- **Random sort is non-idempotent**: `web/lib/search.ts:132-138` reshuffles on any incidental
  recompute of the `useMemo`. Seed per-session or shuffle once.
- **A11y labels**: search inputs (`components/Hero.tsx:15`, find-my-name input) are
  placeholder-only; sort `<select>` (`SearchExperience.tsx:60`) has no aria-label; hamburger menu
  (`components/Header.tsx:26-51`) has `aria-expanded` but no `aria-controls`/id link or focus
  management.
- **Fonts**: three Google families loaded (`layout.tsx:6-8`); Inter is almost never rendered
  (all-Armenian content, `--font-arm` first in the stack) yet still fetched.
- **Soundboard placeholder promise**: `app/soundboard/page.tsx:20` shows "🔊 Ձայնը՝ շուտով" -
  either build the audio (see B2) or drop the promise.
- **Multi-word fuzzy is weak** (minor): the Fuse index is single words, so a multi-word typo query
  ("barev dzes") compares the whole query string against individual words and matches poorly.
  Could split the query into words and fuzzy-match each.
- **Related-list popularity loop** (content, minor): `web/lib/related.ts` tie-breaks by view count
  and 76% of sketches share the Hayko/Mko duo, so the same few mega-hits appear as "related" on
  hundreds of pages. A deterministic per-target shuffle among near-equal scores would diversify.

Verified non-issues (don't re-investigate): theme flash prevention is correct
(`layout.tsx:16` + ThemeToggle lazy init); `related.ts`/`facets.ts` memoization is correct for the
702-page build; WatchView is a server component so `related(s, ALL)` runs at build time and only 6
sketches serialize to the client; `translit.ts` digraph-before-single ordering is correct.

---

## B. Data inventory - what exists but the site never uses

- **`data/youtube_metadata.csv` has 27 columns; only 4 reach the site** (`video_id, duration_sec,
  view_count, upload_date` via `_METADATA_COLS` in `scripts/kargin_build/assemble.py`). Unused and
  rich: `like_count`, `comment_count`, `tags` (per-video keyword arrays), `description`,
  `chapters_json`/`chapters_count`, `categories`, `subs_manual_langs`, `has_auto_captions`.
- **`data/transcripts/` = 315 JSON files covering 274 distinct videos** with REAL timestamped
  events: `{video_id, seq, title, source_lang, n_events, duration_sec, full_text,
  events: [{start, end, text}]}` (float seconds, e.g. `start: 0.73`). Source langs: hy=84 (native
  Armenian), en=49, tr=92, ru=24, etc. Zero references to transcripts anywhere in `web/`.
- **`data/audio/` = all 702 sketch audio files** (webm/opus, 1.6 GB, local only). Site uses none.
- **`data/transcripts_gemini/`** = 6-video Gemini STT spike (pro + flash-lite) with quality
  comparison - proof Armenian ASR works; full-archive run still pending (PROGRESS "Next").
- **`stats.json`** blocks that are typed but under-visualized: `coOccurrence.matrix` (7x7),
  `nameSuggestions`, `topWords`, `viewsBySeq`.
- **`web/lib/quizzes.ts`**: 3 levels / 15 questions, all hand-authored; every answer is already a
  computed fact in `stats.json`.
- The soundboard's 12 tiles come from `stats.json.topPhrases` via `web/lib/soundboard.ts` -
  precomputed at build (good pattern to extend).

---

## C. Creative ideas (prioritized, with what powers them)

### Data-ready today - no new pipeline

1. **Jump-to-the-moment NOW for 274 videos.** Don't wait for Gemini: wire the existing
   `data/transcripts/` events into a `segments[]` field (re-add to `types.ts` + build - it was
   removed in the 2026-06-22 cleanup because it was always empty), make the watch-page timestamp
   chips clickable `?t=Ns` deep links, label coverage as partial. De-risks the flagship feature
   for free; Gemini later upgrades coverage 274 -> 702.
2. **Real soundboard audio.** All 702 audio files exist locally + phrase timestamps for covered
   videos -> clip 2-4s catchphrase mp3s at build time, make tiles actually play. A soundboard
   that makes sound gets shared; one that navigates is a link list.
3. **Quiz generator.** Generate unlimited rounds at build from `sketches.json`/`stats.json`:
   "who said it" (quote -> actor), "which sketch is this catchphrase from", higher/lower on view
   counts (proven addictive format), "guess the year from the thumbnail". Replaces the 15
   hardcoded questions and fixes their stale-fact problem in one move.
4. **Surface likes/comments/tags.** Add `like_count`, `comment_count`, `tags` to `_METADATA_COLS`
   -> "most loved" (like/view ratio) and "most discussed" leaderboards (different signal than raw
   2013 views), tag facets in search, better related-sketches.
5. **Sketch of the day.** Deterministic date-hash pick featured on the home hero, one shareable
   URL per day. Cheapest possible return-visit habit; pairs with the OG work (A1) so the daily
   link previews well in chats. Variant: "on this day" from uploadDate.
6. **Timeline page.** `uploadDate` on all 702 + `viewsBySeq` (already computed): scrubable
   2012-2013 release timeline with view spikes annotated.
7. **Actor chemistry network graph.** `coOccurrence.matrix` is computed and typed but barely
   shown. Interactive network, click an edge -> sketches with that pair.
8. **Quote share cards.** Canvas-render a catchphrase over the flag-color design system as a
   downloadable PNG. The audience shares Kargin quotes constantly; give them a branded artifact.
   Same machinery later powers the personal-stats export (C11).

### Needs the logger live (argues for finally doing the Neon + Worker setup, see logger-worker/README.md)

9. **Best-sketch bracket tournament.** One matchup a day, community votes stored via the existing
   logger worker (tiny schema addition). Creates daily return visits + a "community top 100" that
   view counts can't give (views measure 2013 YouTube, not today's fans).
10. **Popular searches / trending quotes** from the query log as tap-to-search chips on home.
    Also reveals what people search and can't find -> prioritizes transcription work.

### No backend, personal

11. **"Your Kargin wrapped"** - localStorage watch/search history -> private stats card (sketches
    watched, top actor, most-searched word), exportable via the C8 share-card machinery.

---

## Suggested pickup order

1. A1 SEO package (1-2 hours, permanent compounding payoff; do A3 contrast fix alongside since
   both touch globals/tokens).
2. C1 wire existing 274 transcripts in (validates jump-to-moment before spending on Gemini).
3. C3 quiz generator + C5 sketch of the day (retention for near-zero effort).
4. A2 bundle fix (needed before the payload grows again when segments land).
5. Full Gemini transcription run (PROGRESS Phase 1A) - upgrades C1 to 702 coverage and unlocks
   full-archive C2 audio clips.
