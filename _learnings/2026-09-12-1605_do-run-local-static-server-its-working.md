# Do not run a local static server with its working directory inside `web/out`

*From LEARNINGS.md, section "2026-09-12 — collections, and four things that looked like bugs but were not".*

**Do not run a local static server with its working directory inside `web/out`.** `next build` then fails with `syscall: 'rmdir', path: ...\web\out` because it cannot delete the directory a process is sitting in. `python -m http.server 3005 --bind 127.0.0.1 --directory web/out` from the repo root serves the same files without holding it.
