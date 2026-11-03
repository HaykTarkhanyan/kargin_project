# API key flow worked first try

*From LEARNINGS.md, section "YouTube Data API v3 vs yt-dlp (2026-04-25)".*

**API key flow worked first try.** Console signup → enable YouTube Data API v3 → create API key → paste in `.env` as `YOUTUBE_DATA_API_KEY`. Project hits the API as 14 batched calls of 50 video IDs each, ~0.5 sec total wall time vs 25+ minutes for yt-dlp.
