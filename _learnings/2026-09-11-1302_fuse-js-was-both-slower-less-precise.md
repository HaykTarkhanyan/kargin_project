# Fuse.js was both slower and less precise than a hand-rolled edit distance, for this shape of problem

*From LEARNINGS.md, section "2026-09-11 — fixing phrase search: what the measurements overturned".*

**Fuse.js was both slower and less precise than a hand-rolled edit distance, for this shape of problem.** Measured over a 68,613-word vocabulary: `fuse.search` 481-1096 ms versus 85-130 ms for a length-bucketed Levenshtein scan, returning 195 candidates for "կառնեմ" where 8 are actually within one edit. Worse, its Bitap score **saturates on short words**: "սարո" scored an identical 0.2500 against "սամո" (the sketch the visitor wanted), "կարող", "պարոն" and 457 others, so no score cutoff could separate a misspelling from a coincidence. Its `limit` option does not help either — it truncates results after scoring the whole vocabulary, so it buys no time and silently drops matches ("սամո" sat 47th).
