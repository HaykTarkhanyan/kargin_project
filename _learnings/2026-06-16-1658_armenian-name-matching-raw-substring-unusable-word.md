# Armenian name matching: raw substring is unusable; word + case-suffix matching is the fix

*From LEARNINGS.md, section "Website v2 — EDA, discovery, layout (2026-06-16)".*

**Armenian name matching: raw substring is unusable; word + case-suffix matching is the fix.** `Անի` as a raw substring matched **365** sketches (94% noise — `պատուհանից`, `անիծել`); declension-aware matching (a *word* equals the name, or starts with it + a known case ending `ին/ի/ից/ով/ում/ը/ն`) gives the real **22**. This solves both over-matching (short names embedded in words) and under-matching (declensions) at once.
