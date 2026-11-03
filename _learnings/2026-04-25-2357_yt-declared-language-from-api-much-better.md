# `yt_declared_language` from the API is much better than yt-dlp's `language` field

*From LEARNINGS.md, section "YouTube Data API v3 vs yt-dlp (2026-04-25)".*

**`yt_declared_language` from the API is much better than yt-dlp's `language` field.** API returns the uploader-declared language (`hy` for Armenian on 578/695 Kargin videos); yt-dlp's auto-detection got fooled by foreign-language song intros and returned `ru`/`es`. The API is the right source for "what language is this video supposed to be in."
