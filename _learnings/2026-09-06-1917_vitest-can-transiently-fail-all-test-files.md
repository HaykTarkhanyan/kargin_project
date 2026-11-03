# Vitest can transiently fail ALL test files right after a big npm install

*From LEARNINGS.md, section "2026-09-06 — Firebase migration (phase 1-3 code)".*

**Vitest can transiently fail ALL test files right after a big npm install** (10/10 files errored with 0ms of tests; identical rerun: 73/73 pass). node_modules churn from `npm i -D firebase-tools` racing the first vitest run is the best explanation. Rerun before debugging.
