# `captions.list` API costs 50 units per video

*From LEARNINGS.md, section "YouTube Data API v3 vs yt-dlp (2026-04-25)".*

**`captions.list` API costs 50 units per video** (vs 1 for `videos.list`). For 695 videos that's 34,750 units, 3.5x daily quota. Not the right tool for bulk caption fetching here — yt-dlp pulls the same data without quota cost.
