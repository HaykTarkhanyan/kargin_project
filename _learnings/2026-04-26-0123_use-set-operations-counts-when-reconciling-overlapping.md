# Use set operations, not counts, when reconciling overlapping data sources

*From LEARNINGS.md, section "Reconciling data sources (2026-04-25)".*

**Use set operations, not counts, when reconciling overlapping data sources.** Counts hide the structure: "200 vs 184" doesn't tell you whether B ⊂ A, B ∩ A = ∅, or anything in between. Set diffs (`A - B`, `B - A`, `A ∩ B`) tell you exactly what's redundant, what's unique, and what to do. Caught a strict subset relationship between two "first 200" sheets this way that count comparisons would have missed.
