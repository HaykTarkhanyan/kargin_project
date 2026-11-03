# `gh run watch --exit-status | tail` reports the TAIL's exit code, not the run's

*From LEARNINGS.md, section "2026-09-04 — Opus second pass, agent-fleet operations".*

**`gh run watch --exit-status | tail` reports the TAIL's exit code, not the run's.** A deploy failed (Pages infra uploaded 3 artifacts after runner retries; deploy-pages refuses ambiguity) and I reported it green because the pipe ate the non-zero exit. The user's GitHub failure email caught what my check missed — the second time in this project that "verify the deploy" failed at the verification itself. Rule: never pipe a command whose exit code you depend on; use `if cmd; then` or check `PIPESTATUS`. And a green report is only as good as the plumbing that carried it.
