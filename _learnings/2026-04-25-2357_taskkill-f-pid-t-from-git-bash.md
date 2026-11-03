# `taskkill /F /PID ... /T` from Git Bash

*From LEARNINGS.md, section "Concurrency & infra (2026-04-25)".*

**`taskkill /F /PID ... /T` from Git Bash** mangles the `/F` flag because Git Bash's MSYS path translation interprets it as a Unix path (`F:/`). Wrap in `cmd //c "taskkill /F /PID ..."` to bypass translation.
