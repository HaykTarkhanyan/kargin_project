# 690/702 annotated; 12 blocked by `PROHIBITED_CONTENT`

*From LEARNINGS.md, section "2026-09-07 - the full sweep: 12 rows blocked by content filter, and it is the CURATED TEXT".*

**690/702 annotated; 12 blocked by `PROHIBITED_CONTENT`** (seqs 44, 67, 80, 112, 254, 279, 399, 410, 438, 649, 666, 693). Isolation probe on seqs 44 and 67: full input BLOCKED, input minus transcript still BLOCKED, title+visual only OK. So the trigger is the hand-curated Armenian dialogue in `kargin_eng.csv`, not the auto-transcript as assumed. These are the crude/explicit sketches; the filter is on the PROMPT (`prompt_feedback.block_reason`), so `safety_settings` cannot relax it.
