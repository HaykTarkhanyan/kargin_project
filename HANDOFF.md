# Handoff

Pick-up note for the next session. Overwritten at the end of each session;
the history lives in `_work_sessions/`. Last written 2026-09-11 by the session
in `_work_sessions/2026-09-11-1759_hearts.toml`.

## State

- **Shipped:** hearts, commit `1e1df40` on `main`, pushed. This note and the
  session log are in the docs commit right after it.
- **Deploy:** green, CI run 34633618094 (build and deploy jobs). Checked live,
  not just the tick: karginhaghordum.am and kargin-archive.web.app both serve
  the JS chunk with the heart code, and a watch page's prerendered HTML has the
  big heart button. The home page HTML is a 10.5 KB shell with no cards, so
  finding no hearts in it is expected. The rules were not read back from the
  Rules API (no gcloud token in the shell); they went out in the same
  `firebase deploy --only firestore,hosting` that demonstrably updated hosting.
- **Nothing running:** no background process, no emulator, no Colab session.

## The working tree is not clean, and none of it is from this session

Another session's work on similar sketches (embeddings, DECISIONS.md #12) is
uncommitted, plus text-annotation work. Do not `git add -A` or `git commit -a`,
and do not commit any of it in pieces without asking the user:

- `web/lib/types.ts` (`similar`), `web/lib/related.ts`, `web/lib/__tests__/related.test.ts`, `web/public/data/sketches.json`
- `scripts/build_site_data.py`, `scripts/kargin_build/assemble.py`, new `scripts/kargin_build/neighbors.py`, new `scripts/embed_annotations.py`, new `scripts/non_essential/build_similarity_report.py` and `compare_embedding_variants.py`
- `scripts/extract_text_annotations.py`, `scripts/non_essential/build_text_annotation_pilot_report.py`, `data/text_annotations*/`, `data/embeddings/`, `data/gemini_spend_ledger.jsonl`
- `domain-dialog.md` (origin unknown, untouched)
- `DECISIONS.md`: #10, #11, #13, #14 (earlier sessions, their code is committed) and #12 are in the working tree but not committed. Only #15 is committed. To commit one entry without the rest, see the notes in the session log.

## Open

1. Hearts have not been looked at in a browser (the Playwright MCP was down). Check that the heart sits top-right on a card thumbnail and tapping it does not open the sketch; that the watch page has the large heart next to Share; and that the home page shows "Իմ սիրածները (N)" after the first heart and the filter works.
2. Once people use it, check that `heart` / `unheart` rows land in the Firestore `events` collection. `scripts/non_essential/report_usage.py` is the existing admin-SDK read path.
3. Carried over: no rate limit on `feedback` beyond the size caps; `fuse.js` is still an unused dependency (user's call); Mher's karginhaghordum.am cutover and the canonical-domain decision.

## Gotchas from this session

- Low memory makes tests look broken: vitest "Timeout waiting for worker to respond", and `npm run test:rules` reporting "19 skipped" with exit 1. Free RAM and rerun before debugging anything.
- `react-hooks/set-state-in-effect` does not look inside a local `sync()` function, so a clean lint is not proof. For `localStorage` state on statically exported pages, `useSyncExternalStore` with a server snapshot is the pattern (`web/components/HeartButton.tsx`).
- A push to `main` is a prod deploy (rules + hosting + Firestore sync). The workflow cancels an in-progress run when a new push lands, so never push twice during a deploy; docs-only commits can use `[skip ci]`.
- `web/lib/log.ts` commits each event batch atomically. A new event type must be in `firestore.rules` no later than the site that sends it, or it takes the events batched with it down too.
