# `yt-dlp`'s `subtitleslangs` option accepts Python regex patterns

*From LEARNINGS.md, section "YouTube transcript fetch (2026-04-26)".*

**`yt-dlp`'s `subtitleslangs` option accepts Python regex patterns.** This is in the docs but easy to miss. Pattern `.*-orig` filters to source-language captions only. Without it, asking for "all" auto-captions writes ~157 files per video — 1 source plus ~156 auto-translation derivatives that are pure noise (Google Translate of the source, not independent transcriptions). With it, you get exactly 1 file per caption-having video.
