# Kargin Archive — Website v2 (EDA, layout, discovery) Design Spec

**Date:** 2026-06-16
**Status:** Draft for review (rev 4 — 3rd pass: fixed the cut-scope contradiction (cross-links needed URL filter seed → home now needs Suspense too), avg-views excludes Այլ, "uncurated" not "no actors", types-drift + SVG a11y)
**Owner:** Hayk
**Builds on:** the live MVP (`docs/superpowers/specs/2026-06-16-kargin-website-ui-design.md`) at https://hayktarkhanyan.github.io/kargin_project/

---

## 1. Scope

Five enhancements to the live site. No backend; still a static Next.js export to GitHub Pages.

1. **Home layout:** move filters from the left rail into the **hero's top-right**; results go **full-width** below.
2. **Watch page right column:** replace the (internal-only) dialogue with a **"this sketch" panel** — catchphrase + clickable actor/location tags + **related sketches**.
3. **Stats page** (`/stats`, nav «Վիճակագրություն»): a rich EDA playground — keep simple bars **and** add scatter, heatmap, trend line, word/phrase fields, distribution, composition.
4. **Find-my-name page** (`/find-my-name`, nav «Իմ անունը»): search a person's name across actors + roles + dialogue, with default name chips and match-type badges.
5. **Copy on watch page:** a convenient **copy-link** and **copy-catchphrase** button. (No social cards / sitemap / shareable-URL machinery — explicitly out.)

### Out of scope
Recently-viewed, sketch-of-the-day, keyboard shortcuts, Open Graph/social cards, sitemap/robots, shareable search URLs, has-dialogue filter, dark mode. (Considered, not chosen.)

## 2. Architecture & data

- **Stats are precomputed at build** by the Python pipeline into `web/public/data/stats.json`. The dialogue tokenization (words, bigrams), co-occurrence matrix, and aggregates belong in Python (build-time), not shipped to the client. The Stats page just renders `stats.json`.
- **Related sketches** and **find-my-name** run **client-side** over the already-loaded `sketches.json` (cheap at 702 rows) — no new build artifact.
- **Charts are hand-rolled SVG + CSS** (no Chart.js/Recharts). Rationale: matches the Kargin Classic brutalist look (hard borders, flag colors), keeps the bundle lean, honors the chart rules (bars not pie, amount labels, flag colors red `#D90012` / blue `#0033A0` / orange `#F2A800`).

## 3. Home layout — filters in the hero (`SearchExperience`)

- Hero becomes two columns: **left** = headline + search + stat strip; **right** = a compact **filter panel** (`HeroFilters`) — Location, Actors (top-N + "more"), Duration chips, Language, each a small collapsible group. On narrow screens it stacks below the search.
- Below the hero: **active-filter chips + clear-all + result count + sort**, then a **full-width grid** (`xl:grid-cols-4`, was 3 with the rail). The 48-cap + "load more" + lazy thumbnails stay.
- `FilterRail` is refactored into `HeroFilters` (same state/logic, new container/sizing). The left-rail markup is removed.
- **Internal link seed (resolves a scope tension):** the home reads simple `?location=<loc>` / `?actor=<name>` params on load to pre-apply *one* filter, so the watch-page tags (§4) and Stats labels (§5) actually land somewhere. This is a tiny internal-navigation slice — **NOT** the full "shareable search URLs" feature that was cut (no `q=`, no multi-filter serialization). Like find-my-name, it uses `useSearchParams`, so the home now **also needs a `<Suspense>` boundary** under static export (another silent build-breaker if missed).

## 4. Watch page right column — "this sketch" + related (`WatchView`)

Replaces the dialogue panel. Left column (player + actions + metadata) unchanged.
- **Top:** the catchphrase as a featured quote (`★ Հանրահայտ տողը`); if empty, omit. Below it, **clickable tags**: actor chips → `/find-my-name?name=<actor>`, location chip → `/?location=<loc>` (the home reads that seed param, §3).
- **Below:** **«Նմանատիպ»** — up to 6 related sketches as compact rows (thumbnail + title + location + views), linking to their watch pages.
- **Related logic** (`lib/related.ts`): the hard part — Հայկո/Մկո appear in **~76%** of sketches, so "shares an actor" matches almost the whole corpus and degrades to "globally most-viewed." Fix = **rarity-weighted scoring**: for each shared actor add `1 / actorFrequency` so a shared *guest* (Հասմիկ, Աշոտ, Ռաֆո…) counts far more than the ubiquitous duo; add a location bonus **only when the location is not `Այլ`** (a 52% catch-all). Sort by score, tie-break by views, exclude self, take top 6. If a sketch has no meaningful overlap (duo-only, `Այլ` location), **fall back to popular sketches from the same era** so the list is never empty or just the same global top-10 on every page. Pure function over `ALL`.
- The curated dialogue stays in the data (`sketches.json`) for internal use; it's just no longer rendered publicly.
- **Copy buttons** live in the left action bar (see §7).

## 5. Stats page (`/stats`)

Renders `stats.json`. Sections, each a bordered card with `5px` offset shadow:
- **Stat band:** sketches, hours, views, actors, months.
- **Insight callouts (3):** ×3 duration→views, Ռաֆո star-power, 51%/25% concentration. (Dark + flag-color cards.)
- **Existing bars (kept):** top actors (count), location (count, with "Այլ = uncurated" note), duration distribution (count), most-viewed 5.
- **New visuals:**
  - **Star-power scatter** (SVG): x = #sketches, y = avg views/sketch, bubble size = presence. Story: leads are high-count/mid-avg; rare guests high-avg.
  - **Co-occurrence heatmap** (CSS grid): actors × actors, cell = shared sketches, orange intensity.
  - **Duration → avg-views trend line** (SVG area+line): monotonic climb to 1.43M.
  - **Signature phrases** (bigrams): «ցավդ տանեմ», «ախպեր ջան»… as a styled bar/field. **This is the stronger content story — lead with it.**
  - **Word field** (secondary, smaller — top single words sized by frequency). Caveat: single words skew to function words (`բայց`/`ասում`/`դուք`/`մենք`), so it needs a tuned stopword list or it's dull; the bigrams carry the flavor.
  - **Cast composition:** solo / duo / ensemble / no-actor as a single stacked bar (not pie).
  - **Views histogram:** the long tail (peak 500K–1M, tail of 27 at 2M+).
  - **Avg views by location:** Խանութ over-performs (lollipop/bar).
  - **Views across the run:** avg views over `seq` (line/scatter).
- **Interactivity:** actor labels → `/find-my-name?name=…`, location labels → `/?location=…` (the §3 seed). Charts are otherwise static — values labeled on the marks (no hover tooltips).
- **Honesty fixes:** the avg-views-by-location chart **excludes `Այլ`** (a catch-all whose average is meaningless); the composition chart labels the 104 actorless rows **«չդասակարգված» (uncurated)**, not "no actors" (they have actors, just uncurated); views-across-the-run covers only the **598** sketches with a parseable `seq`.
- **Components:** `StatBand`, `InsightCard`, `BarList`, `Scatter`, `Heatmap`, `TrendLine`, `WordField`, `StackedBar`, `Histogram` in `web/components/stats/`. Each takes typed props from `stats.json`; no chart library.

### `stats.json` shape (precomputed)
```jsonc
{
  "totals": { "sketches": 702, "hours": 33.9, "views": 492332830, "actors": 13, "months": 10, "from": "2012-06-15", "to": "2013-04-11" },
  "actorsByCount":  [{ "name": "Մկո", "n": 538 }, ...],
  "actorsAvgViews": [{ "name": "Ռաֆո", "n": 22, "avgViews": 1058000 }, ...],
  "locationByCount":[{ "loc": "Այլ", "n": 363 }, ...],
  "locationAvgViews":[{ "loc": "Խանութ", "n": 14, "avgViews": 1182000 }, ...],
  "durationBuckets":[{ "bucket": "<2ր", "n": 167, "avgViews": 495000 }, ...],
  "topViewed":      [{ "seq": 582, "id": "...", "title": "...", "views": 5996952 }, ...],
  "coOccurrence":   { "actors": ["Մկո","Հայկո",...], "matrix": [[0,474,...],[474,0,...],...] },
  "topWords":       [{ "w": "բայց", "n": 625 }, ...],
  "topPhrases":     [{ "p": "ցավդ տանեմ", "n": 257 }, ...],
  "composition":    { "solo": 69, "duo": 289, "ensemble": 240, "noActor": 104 },
  "viewsHistogram": [{ "bucket": "<250K", "n": 105 }, ...],
  "viewsBySeq":     [{ "label": "75-133", "avgViews": 580000 }, ...],
  "extremes":       { "shortestSec": 30, "shortestSeq": 682, "longestSec": 1177, "longestMin": 19.6 },
  "nameSuggestions":[{ "name": "Անի", "n": 22 }, { "name": "Արմեն", "n": 13 }, ...]  // top declension-aware dialogue mentions, for find-my-name chips
}
```
Built by a new `scripts/kargin_build/stats.py` (pure functions: `build_stats(sketches) -> dict`, fully unit-testable) called from `build_site_data.py`, writing `stats.json` next to `sketches.json`.

## 6. Find-my-name page (`/find-my-name`)

- **Hero:** «Գտի՛ր քո անունը» + input + **default name chips**. Chips are **data-derived, not hardcoded** (verified: my first guesses were bad — `Սուրեն`=2, `Կարո/Վանո/Մարո`=0 real matches). Source = the cast (always non-empty) + the top mentioned names from the build (`stats.json.nameSuggestions`, e.g. `Անի`=22, `Արմեն`=13, `Վարդան`=11, `Գագ`=9). Reads `?name=` from the URL so watch-page tag links work.
- **Match — declension-aware WORD matching, NOT raw substring** (`lib/findName.ts`): raw substring is catastrophic for short Armenian names (`Անի` → 365 raw matches, 94% noise like `պատուհանից`; `Կարո` → 192 raw / 0 real). Instead: tokenize each field into Armenian words; a word matches the name if `word === name` **or** `word` starts with `name` followed by a known Armenian declension suffix (`ին, ից, ի, ով, ը, ն, ներ, ներին, …`). This caught the real 22 `Անի` mentions and dropped the 343 false positives. Run across `actors`, `rolesNames`, `textCommon`, `text`.
- **Classify each hit:** 🎭 **actor/role** (matched in `actors`/`rolesNames`) vs 💬 **mentioned** (matched only in dialogue); for 💬, extract the surrounding sentence with the matched word highlighted.
- **Results:** card grid; each card = thumbnail + title + match badge + (for 💬) the highlighted quote + meta. Count header «"Name" — N սքեթչ». Empty state when 0.
- **Static-export gotcha:** the page reads `?name=` via `useSearchParams`, which under `output: 'export'` **requires a `<Suspense>` boundary** around the client component or `next build` fails. The page is a thin client component over `ALL`; keep `findName` separate from `searchSketches` (different output: match-type + snippet) but reuse `normalize()`.

## 7. Copy on the watch page

- A small **`CopyButton`** in the left action bar: **«🔗 Պատճենել հղումը»** copies the canonical sketch URL; **«Պատճենել տողը»** copies the catchphrase (shown only if `textCommon` exists).
- Uses `navigator.clipboard.writeText`; shows a transient "✓ Պատճենվեց" state. Client-only, no dependency.

## 8. Navigation

Header nav gains the two pages back: **Որոնել · Պատահական · Վիճակագրություն · Իմ անունը · Մասին**. Active state per route.

## 9. Files (created / modified)

```
scripts/kargin_build/stats.py            # NEW: build_stats() + helpers (words, bigrams, co-occurrence, aggregates)
scripts/build_site_data.py               # MOD: also write web/public/data/stats.json
tests/build/test_stats.py                # NEW: unit tests for stats helpers
web/lib/related.ts  web/lib/findName.ts  web/lib/stats-types.ts   # NEW
web/lib/__tests__/related.test.ts  findName.test.ts               # NEW
web/components/HeroFilters.tsx           # NEW (from FilterRail)
web/components/SearchExperience.tsx      # MOD: hero-filters layout, full-width grid
web/components/WatchView.tsx             # MOD: "this sketch" + related (replaces dialogue)
web/components/CopyButton.tsx            # NEW
web/components/RelatedList.tsx           # NEW
web/components/stats/*.tsx               # NEW: StatBand, InsightCard, BarList, Scatter, Heatmap, TrendLine, WordField, StackedBar, Histogram
web/app/stats/page.tsx                   # NEW
web/app/find-my-name/page.tsx            # NEW
web/components/Header.tsx                # MOD: 5-item nav
web/app/sketch/[id]/page.tsx             # (unchanged; WatchView swap is internal)
```

## 10. Testing

- **Python:** unit-test `build_stats` helpers on a small fixture (co-occurrence counts, bigram extraction with stopwords, duration buckets, composition). Then run on real data and sanity-check `stats.json`.
- **TS:** unit-test `related()` (shared-actor/location scoring, self-excluded) and `findName()` (match-type classification, snippet highlight, declension substring) with Vitest.
- **Visual:** Playwright screenshot of `/stats`, `/find-my-name`, the new home, and a watch page from the static build.

## 11. Risks / notes

- **Find-my-name precision (RESOLVED, verified on real data):** raw substring is unusable for short names — `Անի` matched 365 sketches (94% noise: `պատուհանից`, `անիծել`), `Կարո` 192/0-real. Fix = declension-aware word matching (word == name OR name + known suffix), which yields the true 22 `Անի` mentions. The default chips are data-derived from the build, never hardcoded (untested guesses like `Սուրեն`=2, `Կարո`=0 were wrong).
- **`useSearchParams` + static export** (find-my-name `?name=`) needs a `<Suspense>` boundary or `next build` fails. Don't forget it.
- **Small-sample avg-views** — `Ռաֆո` (n=22) and `Խանութ` (n=14) have high-variance averages; always show `n` on the mark/label and don't crown a "star" without showing its small sample. Bubble size = n already encodes this.
- **Scatter label collision** — `Մկո` (538/677K) and `Հայկո` (532/680K) sit almost on top of each other; offset their labels (one above, one below) or they overlap.
- **Hero filter panel must stay compact** — use collapsed groups / dropdowns in the hero's right column, not the full expanded checkbox rail, or the hero grows absurdly tall. Active-filter chips live above the full-width results.
- **Heatmap/scatter readability** — keep to the top ~7 actors; label marks directly (no hover for static).
- **Word/bigram quality** depends on the Armenian stopword list; start small, expand from the build's own output (same loop as the MVP actor-allowlist refinement).
- **`stats.json` size** is tiny (aggregates only) — safe to commit.
- **Filters scroll away while browsing** — with filters in the hero, adding a filter mid-scroll means scrolling back up. The active-filter chips above the results handle *removal* in place; adding is a scroll-up (acceptable for a browse page; revisit a sticky compact filter affordance if it annoys).
- **Declension suffix list** — use the real Armenian case endings (`ին, ի, ից, ով, ում, ը, ն`) and validate against the build's own output; avoid over-broad single letters (e.g. `ե`) that inflate matches. Same tuning loop as the stopword list.
- **Copy** uses `window.location.href` (carries the basePath) + `navigator.clipboard` (secure context — GitHub Pages is HTTPS, localhost is fine).
- **Stats page is large** (~12 visualizations) — fine since you asked for depth, but **section it** ("Cast" / "Reach & views" / "Language of Kargin") so it's navigable, and build it in chart-component increments. Easy to trim later if it feels heavy.
- **`stats-types.ts` ↔ `stats.json` drift:** the TS types are hand-mirrored from the Python output, so a field rename in `stats.py` silently breaks the Stats page at runtime (not at build). Keep both adjacent in the plan; add a light shape-assert when loading `stats.json`.
- **SVG chart accessibility:** hand-rolled charts aren't accessible by default — give each `role="img"` + an `aria-label`/`<title>` stating the takeaway (e.g. "longer sketches average more views"), since there's no underlying table.

## 12. Success criteria

The home uses its full width with filters top-right; a sketch page invites you to keep watching (related) and to copy/share it; «Վիճակագրություն» is a genuinely interesting EDA page (not just bars); «Իմ անունը» finds where a name appears and how. All static, on GitHub Pages, in the Kargin Classic look.
