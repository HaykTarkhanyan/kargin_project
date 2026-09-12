# Collections design

**Date:** 2026-09-12 · **Status:** approved by the owner in session; implemented while the owner is away

Group sketches by the situation they share ("they play cards", "they watch TV")
and give the site a section where those groups can be browsed. Themes come from
hand curation, not from the search filters, because the filters already cover
location, actor and language.

## What the owner chose

1. A sketch can be in several collections. One CSV column holds `;`-separated slugs.
2. Membership is seeded from the annotations and approved by a human, not generated at build time.
3. Collections are reachable from both a strip on the home page and a top-nav entry.
4. A tile shows a 2x2 mosaic of member thumbnails, the name, the sketch count and a one-line description.
5. The first four: cards/backgammon, watching TV, doctor/hospital, traffic police.
6. Collections live in their own data file. `sketches.json`, the `Sketch` type, the
   Firestore mirror and the Telegram bot are untouched.

Point 6 is the load-bearing one. Everything a sketch carries ships inside the home
page's JavaScript (`web/lib/data.ts` is imported by the client component
`SearchExperience`), and the bot's image copies `web/lib` plus `sketches.json`.
Keeping collections separate keeps both out of it, and keeps this change clear of
`types.ts`, `assemble.py` and `sketches.json`, which other sessions have edits in.

## Data

`kargin_eng.csv` gains `collections` as its last column, blank on all 702 rows.
Values are `;`-separated ascii slugs, for example `cards;tv`.

`scripts/add_collections_column.py` adds it, modelled on `add_status_final.py`:
adds the column only if missing, compares every pre-existing column before and
after and refuses to write if any changed, backs up to `data/backups/`, and writes
with `lineterminator="\r\n"` because 114 quoted fields contain embedded newlines.

`data/collections.csv` (new, hand-edited, committed) defines the collections:

| column | meaning |
|---|---|
| `slug` | ascii id, `[a-z0-9_]+`, and the URL segment |
| `name_hy` | Armenian display name |
| `description_hy` | one line shown on the tile and the collection page |
| `sort` | integer, order on the index and the home strip |

Slugs are the URL (`/collections/cards/`), so renaming an Armenian name never
breaks a link. This deliberately differs from the actor pages, which put raw
Armenian in the path.

Do not run `scripts/annotate_kargin_csv.py` after this lands. It rewrites the
header as `id, *others, video_id, duplicate_of`, which would move `status_final`
and `collections` ahead of `video_id`. Pre-existing quirk, recorded here because
the new column makes it easier to trip over.

## Build

`scripts/build_collections.py` (new, top level, load-bearing) reads
`kargin_eng.csv` and `data/collections.csv` and writes
`web/public/data/collections.json`:

```json
[{ "slug": "cards", "name": "...", "description": "...", "sketchIds": ["abc", "def"] }]
```

Ordered by `sort`. Member order is not baked in; the site sorts by view count, so
the build stays independent of `youtube_metadata.csv`. Logs to
`logs/build_collections.log` like the other scripts.

It is a separate script rather than a call inside `build_site_data.py`: collections
do not depend on YouTube metadata, songs, transcripts or visuals, and
`build_site_data.py` currently carries another session's uncommitted edits.
`.github/workflows/deploy.yml` gets one new step after "Build site data".

Every one of these fails the build loudly, with no default and no skipping:

- a slug used in `kargin_eng.csv` that `data/collections.csv` does not define
- a defined collection with zero members
- a duplicate slug in `data/collections.csv`
- a slug outside `[a-z0-9_]+`
- a member `video_id` that is not a sketch in the CSV

## Website

`web/lib/collections.ts` (new) loads `collections.json` and exposes
`allCollections()`, `collectionBySlug(slug)` and `collectionsForSketch(id)`.
Server components only. Nothing reachable from the bot's import graph may import
it; CI's bot job fails if that ever happens.

- `/collections` - heading plus a grid of `CollectionTile`.
- `/collections/[slug]` - `generateStaticParams` over the slugs, then name,
  description, count and a `SketchGrid` of all members sorted by views. No 48-card
  cap: collections are small by construction. Revisit if one passes about 60.
  `notFound()` for an unknown slug, like the actor page.
- `CollectionTile` - 2x2 mosaic of the four most-viewed members' thumbnails, name,
  `N սքեչ`, description. Degrades to however many thumbnails exist when a
  collection has fewer than four members.
- `CollectionStrip` - up to three tiles plus "see all", on the home page between
  the hero filters and the results header. `app/page.tsx` renders it and passes it
  into `SearchExperience` as a `strip` prop, which `Experience` drops between the
  hero section and `<main>`. Passing a server-rendered element keeps
  `collections.json` out of the browser bundle. It does NOT put the tiles in the
  static HTML: `SearchExperience` wraps `Experience` in a Suspense boundary and
  `Experience` reads search params, so the export emits only the fallback and the
  whole home page below the header renders after hydration. The strip therefore
  appears with the hero and the results, which is the existing behaviour of that
  page, and `/collections` is the statically rendered surface for this content.
- `Header.tsx` - an eleventh nav entry, `Հավաքածուներ`. The bar is `xl:flex` and its
  comment already warns that nine Armenian labels overflow a 1024px bar, so the fit
  is checked at 1280 and 1440 before shipping. If it clips, the fallback is a
  shorter label; moving an existing entry into the hamburger is the owner's call.
- `WatchView.tsx` - a collection chip beside the location and actor chips, computed
  at build time.

No changelog entry yet: `web/lib/changelog.ts` is uncommitted in the quiz session.

## Curation

1. `scripts/non_essential/seed_collection_candidates.py` greps
   `data/visual_annotations/*.json` and `data/text_annotations/*.json` per theme and
   writes `data/collections_candidates.csv`:
   `theme,video_id,kargin_id,title,evidence,source,include`. `evidence` is the
   matching phrase, so a row can be judged without opening the video.
2. A human marks `include` as `y`.
3. `scripts/non_essential/apply_collection_candidates.py` turns the ticked rows into
   `data/corrections.csv` rows (`video_id,field,old_value,new_value,edited_at`, with
   `field=collections`), and the existing `apply_corrections.py --write` applies them
   with its backup and validation. Two themes for one sketch merge into one
   `;`-joined value.

Routing through the corrections path means collection edits get the same backup,
the same `plan()` validation and the same audit trail as any other curation change.
`plan()` refuses a correction to a column the CSV does not have, so the column must
exist first.

**The owner is away for this implementation.** Step 2 is therefore done by me, kept
deliberately strict: a row goes in only when the evidence names the situation, not
merely the object. A television in the background of a shop is not "watching TV".
The candidates file is committed with my marks so any row can be changed and
re-applied without redoing the search. Expected sizes after that filtering: cards
10-15, tv 10-20 of 47 raw hits, doctor 40-60, traffic police about 20.

## Tests

Python, `tests/build/test_collections.py` (next to the existing `kargin_build`
tests): each build validation above, `;` parsing with stray spaces and duplicates,
and the candidates-to-corrections conversion including the merge of two themes for
one sketch and the blank `old_value` for a first-time write.

Web, vitest and RTL: `collections.ts` lookups; `CollectionTile` rendering name,
count and four thumbnails; a tile for a collection with fewer than four members.

Then the existing suites must stay green, including the bot job, plus a Playwright
pass at 390 and 1280 px.

## Out of scope

- A collection filter chip on the home page. The collection page is the filter.
- Mirroring collections into Firestore.
- Fixing `annotate_kargin_csv.py`'s column reordering.
- Nothing here is deferred for the changelog after all: the quiz session's
  `changelog.ts` was committed during this work, so the entry went in with it.
- Static HTML for the home strip, for the Suspense reason above. Fixing that would
  mean lifting the hero out of the Suspense boundary, which is a refactor of
  another feature's component and not part of this work.
