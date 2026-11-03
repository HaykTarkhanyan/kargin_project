# Ground-truth from usage logs beats intuition for judging a search change

*From LEARNINGS.md, section "2026-09-11 — fixing phrase search: what the measurements overturned".*

**Ground-truth from usage logs beats intuition for judging a search change.** The events collection records the search and the sketch opened right after, so a change can be scored on a real journey: a visitor searched `սարո` and opened a sketch whose role is **Սամո** — a one-letter miss. That single data point caught a regression (the word-boundary index I had built lost substring matches Armenian suffixes depend on) and then proved the fix: old put the target at #385 of 507, new at #49 of 68, and the correct spelling at #4 of 13.
