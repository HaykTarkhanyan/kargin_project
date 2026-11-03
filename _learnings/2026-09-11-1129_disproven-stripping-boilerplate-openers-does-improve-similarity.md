# DISPROVEN: stripping boilerplate openers does not improve similarity

*From LEARNINGS.md, section "2026-09-08 - DISPROVEN: stripping boilerplate openers does not improve similarity".*

**Theory.** 467 of 702 detailed summaries open with a formulaic phrase ("The sketch
takes place in...", "The sketch begins with..."). That shared lexical prefix should
inflate the similarity floor and compress the useful range into 0.70-0.85, so
removing the lead-in (keeping the setting words after it) should spread the
distribution and sharpen neighbour quality.

**Test.** Re-embedded all 702 with the opener stripped (590 summaries changed) into
side-by-side artifacts (`*__stripped.npz`), then compared on identical metrics.

**Result - half right, and the half that mattered was wrong.**

| metric | full | stripped |
|---|---|---|
| background mean (the floor) | 0.5534 | **0.4582** |
| separation, sd above background | 2.289 | **2.631** |
| topic Jaccard at rank 1 | **0.4559** | 0.4406 |
| known duplicates ranked #1 | 23/23 | 23/23 |

The floor did drop by 0.095 and relative separation improved, exactly as predicted.
But neighbour *quality* did not. Judged at matched percentiles (the only fair
comparison once the scales shift - fixed thresholds are meaningless across
variants), `full` has higher topic agreement in **every** band: top 0.01% 0.841 vs
0.783, top 0.1% 0.494 vs 0.468, top 0.5% 0.371 vs 0.347, top 1% 0.321 vs 0.297,
top 2% 0.284 vs 0.263. Top-1 neighbours changed for 306/702 sketches (43.6%) and
qualitatively the swaps are a wash at best - "The Director's Order and the
Secretary" lost "The Boss and the Seductive Secretary" as its top match.

**Why it probably failed.** The opener is not pure noise: it carries the setting
("...in a rural village cattle barn"), and the shared frame appears to act as a
useful alignment anchor rather than a distraction. The floor was never the problem.

**One nuance in stripped's favour**: at the very top band it recovered 22/25
duplicates vs full's 20 - removing the shared frame makes near-identical texts
stand out. Irrelevant here, since audio fingerprinting already finds duplicates.

**Decision: `full` stays the shipping variant.** Both sets of artifacts are kept
side by side; `embed_annotations.py --variant` selects, default `full`.
