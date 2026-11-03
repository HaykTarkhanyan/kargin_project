# yt-dlp's ffmpeg merger adds `-movflags +faststart` unconditionally

*From LEARNINGS.md, section "2026-09-03 — 360p corpus, contact sheets, visual annotations".*

**yt-dlp's ffmpeg merger adds `-movflags +faststart` unconditionally** (verified in its source), and YouTube's own format 18 already has moov at the front — so range-read-friendly files come free on both paths.
