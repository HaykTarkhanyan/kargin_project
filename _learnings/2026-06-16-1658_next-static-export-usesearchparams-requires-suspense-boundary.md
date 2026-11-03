# Next static export + `useSearchParams` REQUIRES a `<Suspense>` boundary or `next build` fails

*From LEARNINGS.md, section "Website v2 — EDA, discovery, layout (2026-06-16)".*

**Next static export + `useSearchParams` REQUIRES a `<Suspense>` boundary or `next build` fails.** Applies to *any* page reading query params — both find-my-name (`?name=`) and the home's `?location=`/`?actor=` seed. The Suspense'd page becomes client-rendered (brief fallback, then hydrates) — fine for these, but it means the home is no longer static-HTML content.
