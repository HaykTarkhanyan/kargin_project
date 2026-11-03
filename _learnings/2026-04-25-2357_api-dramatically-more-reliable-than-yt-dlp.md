# API is dramatically more reliable than yt-dlp

*From LEARNINGS.md, section "YouTube Data API v3 vs yt-dlp (2026-04-25)".*

**API is dramatically more reliable than yt-dlp** for bulk metadata: no cookies, no rate-limit anti-bot, batches up to 50 ids per call. Cost: 1 quota unit per `videos.list` call regardless of batch size, so 695 videos = 14 units (free quota is 10,000/day).
