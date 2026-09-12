# Handoff

Pick-up note for the next session. Overwritten at the end of each session; the
history lives in `_work_sessions/`. Last written 2026-09-12 by the session in
`_work_sessions/2026-09-12-1445_collections.toml`.

## State

- **Collections shipped.** A new section grouping sketches by situation: four
  collections (Թուղթ խաղում են 3, Հեռուստացույցի առաջ 12, Բժշկի մոտ 44,
  Ճանապարհային ոստիկանը 21), an index at `/collections`, a page per collection, a
  three-tile strip on the home page, a chip on each sketch page and a nav entry.
  Spec `5e6727d`, feature `71e8e0e`, nav fix `4b10ba6`, DECISIONS #17.
- **Nothing is uncommitted any more.** The work three other sessions had left in
  the tree is committed and pushed: embeddings similarity (#12), the quiz levels
  (#16), the text annotation sweep, the Google Forms parse, the DNS step 1b note,
  DECISIONS #10 through #16, and both session logs. Ten commits, one push.
- **Deploy:** green. CI runs 34691981838 (the ten commits) and 34692548934 (the nav
  fix), build and deploy jobs successful on both. Verified on the live site rather
  than by the green tick: `/collections` lists all four with counts 3/12/44/21,
  `/collections/doctor/` renders its 44 cards at phone width with no sideways
  scroll, sketch `rh2-lZwbQ9s` carries both of its chips, and the header overflow is
  gone at 1280, 1300 and 1366.
- **Nothing running:** no background process, no local server, no emulator.

## Waiting on you

1. **The Armenian in `data/collections.csv` is my draft.** Names and descriptions
   both, the same way the quiz wording came to you for review. Rewrite freely, then
   `PYTHONPATH=scripts uv run python scripts/build_collections.py` and commit;
   nothing else needs rebuilding. `Հավաքածուներ` is also just my pick for the
   section name, `Թեմաներ` may read better.
2. **Collection membership is my judgement, not yours.** You were away, so I made
   the include calls: 80 memberships kept out of 286 proposals.
   `data/collections_candidates.csv` holds every proposal with the phrase that
   matched it and my marks. Change any row and re-run
   `scripts/non_essential/apply_collection_candidates.py --write` then
   `scripts/apply_corrections.py --write`. My rule was deliberately strict: a
   television among the props is not "watching TV", and "doctor" required a medical
   setting, which cut it from 109 candidates to 44 members.
3. **`data/google_forms/` images are local only.** 53 screenshots, 21 MB. That
   session had left the decision open, and committing them is the one choice here
   that cannot be undone without rewriting history, so I gitignored the images and
   committed the parsed JSON and notes beside them. If you want them in git, delete
   the two ignore lines and commit.
4. **The unhearted heart is nearly invisible** on a card thumbnail: a white heart
   emoji on a near-white circle. I found it in the visual pass, flagged it, and left
   it alone since hearts had already shipped. The fix is a dark outline glyph (♡)
   in place of 🤍, two lines in `web/components/HeartButton.tsx`.
5. **`domain-dialog.md`** is an accessibility dump left by a Playwright session, not
   a document. Still untracked. Delete it if you agree.

## Gotchas

- Low memory makes tests look broken: vitest "Timeout waiting for worker to
  respond", and `npm run test:rules` reporting "19 skipped" with exit 1. Free RAM
  and rerun before debugging.
- A push to `main` is a prod deploy (rules + hosting + Firestore sync), and the
  workflow cancels an in-progress run when a new push lands. Never push twice
  during a deploy; docs-only commits can use `[skip ci]`.
- `react-hooks/set-state-in-effect` does not look inside a local `sync()` function,
  so a clean lint is not proof. For `localStorage` state on statically exported
  pages, `useSyncExternalStore` with a server snapshot is the pattern.
- Do not run a local static server with its working directory inside `web/out`: it
  stops `next build` from deleting the folder. Use
  `python -m http.server 3005 --bind 127.0.0.1 --directory web/out`.
- Internal links here carry no trailing slash; `next/link` plus `trailingSlash:
  true` canonicalises the exported path.
- A nav item is not free: eleven Armenian labels need 992px, and a 1280px window
  leaves 1265px of layout width once the scrollbar is out.
- `404`s for `__next.*.txt?_rsc=` under a local static server are Next's prefetch
  payloads, not a broken page. They happen on existing routes too.

## Rebuilding the site data

```
PYTHONPATH=scripts uv run python scripts/build_site_data.py    # sketches.json
PYTHONPATH=scripts uv run python scripts/build_collections.py  # collections.json
```

CI runs both on every push. Do not run `scripts/annotate_kargin_csv.py`: it
rewrites the CSV header order and would move `status_final` and `collections`
ahead of `video_id`.
