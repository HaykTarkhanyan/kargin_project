# `npx vitest run` inside a chained *background* shell (no TTY) can report "no tests" spuriously

*From LEARNINGS.md, section "Website v2 — EDA, discovery, layout (2026-06-16)".*

**`npx vitest run` inside a chained *background* shell (no TTY) can report "no tests" spuriously.** A clean foreground re-run found all 14. Don't trust a single "no tests" from a backgrounded gate — re-run in the foreground before concluding the suite is broken.
