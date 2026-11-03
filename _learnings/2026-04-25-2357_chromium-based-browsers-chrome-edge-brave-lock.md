# Chromium-based browsers (Chrome, Edge, Brave) lock their cookie DB while running on Windows

*From LEARNINGS.md, section "Concurrency & infra (2026-04-25)".*

**Chromium-based browsers (Chrome, Edge, Brave) lock their cookie DB while running on Windows** — yt-dlp errors with `"Could not copy Chrome cookie database"` (issue #7271). Workarounds: (a) close all Chrome windows briefly, (b) use Firefox, which doesn't lock, or (c) export cookies via a browser extension and use `--cookies <file>` instead.
