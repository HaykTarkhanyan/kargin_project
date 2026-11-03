# Zero-result queries are the useful signal in a tiny dataset

*From LEARNINGS.md, section "2026-09-11 — the prefetch 404s were a local-serving ghost, and what usage data says".*

**Zero-result queries are the useful signal in a tiny dataset.** 121 events is far too little for trends, but 13 zero-result queries pointed straight at a real product gap (multi-word phrase search — see `DEFERRED_TODO.md`) that no amount of aggregate counting would have surfaced. With small usage data, read the failures individually rather than charting the totals.
