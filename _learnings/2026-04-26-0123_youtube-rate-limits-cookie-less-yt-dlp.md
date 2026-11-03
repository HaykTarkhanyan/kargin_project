# YouTube rate-limits cookie-less yt-dlp at concurrency, not at total volume

*From LEARNINGS.md, section "Concurrency & infra (2026-04-25)".*

**YouTube rate-limits cookie-less yt-dlp at concurrency, not at total volume.** First metadata run with 8-worker `ThreadPoolExecutor` hit `"Sign in to confirm you're not a bot"` around ~150 cumulative requests. But the 2026-04-26 audio download of all 702 videos serially (single-threaded, ~4 sec/video, ~45 min total, no cookies) finished cleanly with zero failures. Implication: the trigger is concurrent connections, not request count. Fix when needed: `cookiesfrombrowser=("firefox",)` in yt-dlp opts (or `--cookies-from-browser firefox` on the CLI). Chromium-based browsers lock their cookie DB on Windows — Firefox is the easy choice. Plan: prefer single-threaded for bulk yt-dlp operations; only reach for parallelism when single-threaded throughput becomes the actual bottleneck.
