# Opus vision agents stall under heavy image work; design for it

*From LEARNINGS.md, section "2026-09-04 — Opus second pass, agent-fleet operations".*

**Opus vision agents stall under heavy image work; design for it.** First escalation wave: 3 of 4 Opus agents died mid-run (one API error, two "no progress for 600s" stream stalls), all while crop-zooming tiles. Sonnet agents ran the identical workflow ~40 times without one such death. Mitigations that worked: (1) agents write each output file THE MOMENT it is done, never batching writes — so a dead agent loses only its in-flight item; (2) recovery relaunches only untouched files (diffed by mtime against the pre-launch commit's timestamp); (3) smaller batches (7 not 13) and fewer concurrent (3 not 4) on retry. The retry wave then ran 11 batches with zero deaths.
