# A piped `grep` masks the script's exit code

*From LEARNINGS.md, section "2026-09-07 - the full sweep: 12 rows blocked by content filter, and it is the CURATED TEXT".*

**A piped `grep` masks the script's exit code.** The sweep ran as `python ... | grep -E ...` and the harness reported "exit code 0" while the script itself had raised `SystemExit(1)` for the 12 failures. Never read success from a pipeline's exit status - check the script's own summary line (or set `PIPESTATUS`/`-o pipefail`).
