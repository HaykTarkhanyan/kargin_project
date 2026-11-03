# A `done` boolean / curation flag scales better than a "needs_review" sidecar

*From LEARNINGS.md, section "Reconciling data sources (2026-04-25)".*

**A `done` boolean / curation flag scales better than a "needs_review" sidecar.** When kargin_eng.csv had `done = 1.0` for curated rows, the cleanest way to flag the 6 newly-added unstubbed rows was just `done = 0.0` — pattern continued, no new column needed, downstream filters work unchanged.
