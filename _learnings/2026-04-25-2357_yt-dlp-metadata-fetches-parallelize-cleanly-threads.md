# yt-dlp metadata fetches parallelize cleanly with threads

*From LEARNINGS.md, section "Concurrency & infra (2026-04-25)".*

**yt-dlp metadata fetches parallelize cleanly with threads.** I/O-bound, ~2s wall time per call serial → ~0.25s effective with 8 workers. ThreadPoolExecutor + per-call `yt_dlp.YoutubeDL(...)` instances (don't share an instance across threads). 8 workers is fine; haven't tested higher.
