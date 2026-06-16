# Kargin Archive — Website UI Design Spec

**Date:** 2026-06-16
**Status:** Draft for review (rev 4 — independent review applied: real `titles`, substring search via scan/Fuse not MiniSearch, real coverage numbers, actor splitter + empty-states)
**Owner:** Hayk
**Related:** [PLAN.md](../../../PLAN.md) Phase 3, [PROGRESS.md](../../../PROGRESS.md)

---

## 1. North star

> "Search Kargin sketches by meaning or exact quote, jump to the moment, in Armenian."

This iteration delivers a **beautiful, deployable web app over today's curated data** (702 sketches), hosted free on **GitHub Pages**. It is the same UI that semantic / spoken-quote search will plug into later — the data model and watch view leave explicit seams for transcripts, but nothing in this build depends on the Gemini pipeline being finished.

**Honest limit of this iteration:** today's `text` (dialogue) column is *hand-curated and often partial*. So MVP exact-quote search recall is **bounded by curation coverage** — it finds quotes that were transcribed by hand, not every spoken line. True "find any line" arrives with the Gemini transcripts (a later phase). The UI is built so that upgrade is a data swap, not a redesign. (See §13 Risks.)

Concretely (verified against the CSV): **100 of 702 sketches have no curated dialogue at all** (`text` empty), 147 have no catchphrase, ~96 no actors, ~91 no location. The site must show *real* coverage ("≈602 of 702 have dialogue") and never imply all 702 are quote-searchable.

## 2. Scope

### In scope (this iteration)
- **Home / Search** — hero + instant client-side search + filters + results grid.
- **Watch view** — `/sketch/[id]` page (player + curated dialogue); shareable URL.
- **Random** — surprise-me into a sketch.
- **About** — what this is, data source, links.
- **Build-time data pipeline** — Python script turns the two CSVs into the JSON the site ships, **canonicalizing messy facets**.
- Deploy as a **pure static site to GitHub Pages**.

### Deferred (not built now)
- **Usage logging** — capture searches/clicks. Deferred per owner. Design seam kept (§11) so it drops in later (browser → Supabase, or a small endpoint) without rework.
- **Stats** (Վիճակագրություն) — EDA dashboard. Easy once data JSON exists; nav slot reserved.
- **Find-my-name** (Իմ անունը) — needs Armenian declension/diminutive matching (PLAN.md Phase 5).
- **Semantic search** — needs embeddings over Gemini transcripts. Toggle shown disabled ("շուտով").
- **Timestamped jump-to-moment** — needs transcript segments. Watch view reserves the slot.

### Out of scope (per PLAN.md)
User accounts, favorites, mobile app, multi-language UI, auth, third-party REST API.

## 3. Tech stack & rationale

| Choice | Decision | Why |
|---|---|---|
| Framework | **Next.js (App Router), static export** (`output: 'export'`) | Highest design ceiling; 702 rows are static; no backend needed once logging is deferred. |
| Styling | **Tailwind CSS** + CSS variables for design tokens | Fast, consistent, token swap if the look ever changes. |
| Search | **In-memory normalized substring scan** (zero-dep, true mid-word match, instant at 702 rows); optional **Fuse.js** for typo-tolerant fuzzy | Quote search needs *mid-word substring*, which MiniSearch's whole-token tokenizer can't do. A normalized `.includes()` scan over 702 short docs is sub-millisecond and exactly right. |
| Data pipeline | **Python build script** (`pandas`) emits JSON | Keeps data work in the existing Python/uv world; decouples pipeline from frontend. |
| Hosting | **GitHub Pages** (via GitHub Actions) | Free, lives in the repo, custom domain supported, great CDN, zero new accounts. |
| Verification | **Playwright** (installed) | Screenshot/check real rendering during build. |
| Design assist | **frontend-design** + **taste-skill** plugins | Distinctive, non-generic execution of the chosen look. |

Design directions were explored in a visual companion; the chosen direction is **Kargin Classic** (see §8).

## 4. Architecture & data flow

```
kargin_eng.csv ─┐
                ├─►  scripts/build_site_data.py  ─►  web/public/data/sketches.json
youtube_metadata.csv ─┘   (pandas; join on video_id;          (consumed at build)
                           canonicalize actors/location/lang)        │
                                                          web/  (Next.js static export)
                                                                        │
                                          browser ── search/filter/sort (client, substring scan)
                                                                        │
                                                   GitHub Pages (static files on CDN)
```

- **Build-time (Python):** join the two CSVs on `video_id`, derive clean fields, **canonicalize facets** (§7.1), write one `sketches.json`. Loud failure on malformed rows (no silent skips), `logging` to `logs/`.
- **Build-time (Next):** export static HTML/JS; pre-render all 702 `/sketch/[id]` pages via `generateStaticParams`.
- **Load-time (client):** fetch `sketches.json` once, build the in-memory index, serve all search/filter/sort in the browser. No server anywhere.

## 5. Repo structure (added by this work)

```
scripts/build_site_data.py        # CSV → sketches.json (Python/pandas), facet canonicalization
web/                              # Next.js app (isolated JS/TS toolchain)
  app/
    layout.tsx                   # shell: header, fonts, theme tokens
    page.tsx                     # Home / Search
    sketch/[id]/page.tsx         # Watch view (shareable page; generateStaticParams over 702 ids)
    random/page.tsx
    about/page.tsx
  components/                    # SearchBar, FilterRail, SketchCard, WatchView, ...
  lib/                           # search.ts, data.ts, format.ts
  public/data/sketches.json      # build artifact
  next.config.ts                 # output:'export', images.unoptimized, basePath (if project page)
  app/globals.css (Tailwind v4 @theme tokens — no config file), package.json
.github/workflows/deploy.yml      # build + publish to GitHub Pages
```

## 6. Pages / surfaces

### 6.1 Home / Search  (`/`)
The validated **v2** layout.
- **Header (sticky):** brand `ԿԱՐԳԻՆ ARCHIVE`; orange active-underline nav. MVP nav: Որոնել, Պատահական, Մասին (Stats + Find-my-name appear when shipped).
- **Hero:** poster headline, large search bar, mode toggle (`Ճշգրիտ` active / `Իմաստային · շուտով` disabled), quick-try chips, red/blue/orange stat strip (702 sketches / 33ժ archive / 488M **cumulative** views — real values from the build), plus an honest "≈602 with dialogue" coverage note.
- **Filter rail (left):** Location, Actors (top-N + "+ ևս N"), Duration (chips), Language — **live counts from canonicalized facets**, flag-blue checks.
- **Results:** active-filter chips + clear-all, result count, sort (views / newest / random), **spacious 3-col grid**. Card = thumbnail (location chip + duration), title, orange-rule quote snippet (match-highlighted on search), actors + views. Hover lifts with red offset shadow + play affordance.
- **Behavior:** instant as-you-type search; filters + search compose; empty / no-results states; `/` focuses search.

### 6.2 Watch view  (`/sketch/[id]`)
- A real, shareable, statically-generated page per sketch.
- **Left:** embedded YouTube player; `▶ Դիտել YouTube-ում`; Copy-link; Random; metadata grid.
- **Right:** curated **dialogue panel**; catchphrase pulled out as `★ Հանրահայտ տողը`. Dashed callout explains timestamps arrive with transcripts; per-line timestamp chips render **disabled** until then (forward-compatible slot).
- Dialogue lines come from a **tolerant splitter** on `;` (≈60% of texts) and `։` (≈30%) — *not* bare `-` (rare, and would mangle `1-2`). The ~100 empty-`text` sketches get an explicit empty-state ("Դեռ չկա ձեռքով համադրված տեքստ", plus the catchphrase/metadata if present) — never a blank panel. See §13.
- **Enhancement (not MVP-blocking):** open as an overlay modal from the grid via intercepting routes *if* it survives static export; otherwise plain-page navigation is the shipped behavior. (Validate in plan; §13.)

### 6.3 Random  (`/random`)
Live shuffle → redirect to a random `/sketch/[id]` (or a reshuffled grid with a "նորից" button). No fixed seed — true randomness is the point.

### 6.4 About  (`/about`)
Short static page: archive description (KarginTV, 702 sketches, 2012–2013), data provenance (hand-curated + YouTube Data API), links. Flag-color editorial styling.

## 7. Search, filtering & data quality

- **Mode (MVP):** `Ճշգրիտ` = normalized **substring** match (mid-word, case/space-insensitive) over **titles, text (dialogue), text_common (catchphrase), main_actors, roles_names, location**, ranked by field weight + match position (boost titles + catchphrase). `Իմաստային` (semantic) shown disabled. **MiniSearch was rejected** — its tokenizer keeps whole tokens and can't match a pasted mid-quote fragment.
- **Optional fuzzy:** typo tolerance via Fuse.js is a post-MVP add; the substring scan is the MVP.
- **Armenian handling:** normalize case + collapse whitespace; fold `ՄԿո`↔`Մկո` style case variants; no transliteration in MVP.
- **Real coverage (verified, not assumed):** ≈602/702 have dialogue `text`, 555 a catchphrase, 606 actors, 611 location. The StatStrip / About must state this honestly; empty-`text` sketches still appear (title + metadata + thumbnail) but cannot match dialogue queries.
- **Filters (compose with search):** location (multi), actors (multi), duration buckets (`<2ր`, `2–4ր`, `4ր+`), language. Counts computed client-side.
- **Sort:** views (default), newest (upload_date), random.
- **Highlighting:** matched terms in the card quote and watch dialogue.
- **Recall ceiling:** bounded by curation coverage (§1, §13). Don't imply exhaustive quote coverage beyond the aspirational hero.

### 7.1 Facet canonicalization (build script) — REQUIRED
Raw columns are messy and **cannot** be used as facets directly:
- **Actors:** ~203 distinct raw strings for ~10 real actors (`Հայկո, Մկո` dominates; also `Հայկո,Մկո`, `Հայկո Մկո`, `Հակյո`, `Հայկո ՄԿո`, trailing commas, plus role-words like `ոստիկան`/`փոքր երեխա` mixed in). Canonicalize: **comma-split first; space-split only when there is no comma** (so `փոքր երեխա` isn't torn apart); trim; match against a small **known-actor allowlist (~10 names)** with a typo map (`Հակյո→Հայկո`, `ՄԿո→Մկո`); tokens not on the allowlist go to `rolesNames`, not `actors`. Output `actors[]` + keep `actorsRaw`.
- **Location:** free-text incl. `Այլ(գրեք ավելացնենք)` and blanks. Map to a small canonical set; bucket unknowns under `Այլ`.
- **Language:** free-text (`հայերեն`, `հայերեն+ռուսերեն`, `այլ`). Normalize to tags.
- Script **emits real facet counts** so the UI never ships fabricated numbers, and a build report lists unmapped values (not silently dropped).

## 8. Visual design system — "Kargin Classic"

Retro Armenian editorial: warm paper, hard ink borders, hard offset shadows, flag-color accents, poster display type. Neo-brutalist-editorial; deliberately *not* generic SaaS.

**Color tokens**
```
--paper   #FBF3E2   page background (warm cream)
--paper2  #F4E9D0   rail / secondary surface
--card    #FFFDF7   card surface
--ink     #1A1410   text, borders, shadows
--muted   #8A7C64   secondary text
--red     #D90012   accent / emphasis (Armenian flag red)
--blue    #0033A0   location chips, checks (flag blue)
--orange  #F2A800   active states, quote rule, primary button (flag orange)
```

**Type**
- Display: **Anton** (Latin) + **Noto Sans Armenian 800** fallback for Armenian glyphs.
- Body/UI: **Noto Sans Armenian** (400–700) + Inter fallback.

**Motifs**
- 2px `--ink` borders; **hard offset shadows** (`6–8px`, no blur).
- Flag-color chips: location = blue pill; emphasis = orange/red.
- Quote snippet = 3px orange left-rule.
- Sticky header, orange active-underline; visible blue focus rings.
- Hover: card translates up-left, shadow turns red.
- **Contrast note:** orange/blue used as fills behind ink/white text only; never small text in orange on cream.

## 9. Component inventory

`Header/Nav`, `Hero`, `SearchBar` (+ mode toggle, quick chips), `StatStrip`, `FilterRail` (`FilterGroup`, `Checkbox`, `DurationChips`, `MoreToggle`), `ActiveFilters`, `ResultsHeader` (count + sort), `SketchGrid`, `SketchCard`, `WatchView` (`Player`, `ActionBar`, `MetaGrid`, `DialoguePanel`, `DialogueLine`), `EmptyState`, `Footer`. Each single-purpose and token-driven.

## 10. Deployment, performance, accessibility

- **GitHub Pages**, published by a GitHub Actions workflow (`build_site_data.py` → `next build`/export → upload artifact → deploy).
- **Static-export config:** `output: 'export'`, `images: { unoptimized: true }` (we use plain `img.youtube.com` thumbnails), `basePath`/`assetPrefix` only if served from a project page (`user.github.io/<repo>`); not needed for a `user.github.io` page or a custom domain.
- **Perf:** lazy-load thumbnails; single `sketches.json` fetch; in-memory index; virtualize the grid only if 702 cards prove heavy (unlikely).
- **A11y:** semantic landmarks, real form controls, visible focus, alt text, keyboard search focus, contrast checked against the paper background.

## 11. Forward-compatible seams

- **Transcripts:** `sketches.json` reserves `segments: []`; watch view already lays out timestamped lines (disabled). Gemini transcripts fill `segments`; lines become clickable `&t=Ns` deep-links — no layout change.
- **Semantic search:** one `lib/search.ts` surface; the *interface* seam is ready and the toggle exists. But it is **not free on pure-static** — it needs pre-computed embeddings shipped to the client (size budget: 702 × vector) + an in-browser similarity search, or it breaks the no-backend constraint. Treat the embedding/size work as its own later task, not a drop-in swap.
- **Usage logging (deferred):** when wanted, add a thin `logEvent()` with a stable schema (`ts, sessionId, type, query, mode, filters, resultCount, sketchId`). On a static host it goes **browser → Supabase** (insert-only key, no backend) or a tiny external endpoint. No part of the current UI blocks this.

## 12. Data model (per sketch)

```jsonc
{
  "id": "ofvCL_U2Er0",            // youtube video_id — the only stable key (702/702 unique)
  "seq": 663,                     // sketch number PARSED from titles via regex; nullable; display-only, NOT an identity
  "title": "Kargin Haghordum sketch 663 (Hayko Mko)",  // REAL `titles` column — never fabricated
  "videoId": "ofvCL_U2Er0",
  "url": "https://youtu.be/ofvCL_U2Er0",
  "thumbnail": "https://img.youtube.com/vi/ofvCL_U2Er0/mqdefault.jpg",
  "text": "…",                   // curated dialogue (raw)
  "lines": ["…", "…"],           // tolerant split for the watch panel
  "textCommon": "արա էսի ուզբեկ ա",
  "actors": ["Հայկո", "Մկո"],    // canonicalized
  "actorsRaw": "Հայկո ՄԿո",      // original, for audit
  "rolesNames": "…",
  "location": "Տուն",            // canonicalized
  "languages": ["հայերեն"],      // canonicalized
  "lighting": "…",
  "durationSec": 242,
  "viewCount": 1358199,
  "uploadDate": "2013-04-10",
  "segments": []                 // [] now; {startSec,endSec,text} after transcripts
}
```
Missing curated values are left empty (no fabricated data). Track `source` per field if/when AI enrichment is added (PLAN.md 1B).

## 13. Risks

1. **Curation-bounded + partial coverage** (§1, §7) — **100/702 sketches have no curated dialogue at all** and won't surface on any quote search; many others are partial. Mitigation: show truthful coverage numbers (≈602 with dialogue); transcripts close the gap later.
2. **Messy facets** (§7.1) — Actors/Location/Language are dirty; filters are only as good as canonicalization. Mitigation: build-script normalization + a report of unmapped values.
3. **Dialogue line splitting** — separators are `;` (≈60%) and `։` (≈30%); bare `-` is rare and would mangle hyphens/numbers. Mitigation: split on `;`/`։` only; empty-`text` (~100 sketches) gets an explicit empty-state.
4. **Intercepting-routes modal under static export** — may not work. Mitigation: ship plain `/sketch/[id]` pages (guaranteed); treat the overlay as an enhancement only if it survives export.
5. **GitHub Pages base path** — project pages need `basePath`; getting it wrong breaks asset URLs. Mitigation: decide user-page vs project-page vs custom-domain up front (§14).

## 14. Open decisions (resolve in plan or with owner)

1. **GitHub Pages URL shape** — `user.github.io` (root, no basePath), a project page `user.github.io/<repo>` (needs basePath), or a custom domain? Decide before wiring `next.config.ts`.
2. **Commit `sketches.json`** to the repo, or generate on build only? (Lean: commit — small, and makes the site buildable without re-running Python.)
3. **Fuzzy mode** — exact substring is a decided zero-dep scan; whether to add Fuse.js typo-tolerance now or post-MVP.
4. **Romanized/Russian search** — out for MVP; revisit.

## 15. Success criteria

A stranger lands on the site, types an Armenian quote or picks filters, sees a beautiful instant result grid (with honest coverage), opens a sketch, and clicks straight to it on YouTube — over the current 702-sketch data, deployed as a pure static site on GitHub Pages, look locked to "Kargin Classic."
