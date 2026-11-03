# Files API upload is fast and cheap

*From LEARNINGS.md, section "Gemini STT spike (2026-04-26)".*

**Files API upload is fast and cheap** (~1-2s per file via `client.files.upload(file=path)`). For the 702-file archive at ~1.5 MB average per ogg, total upload time will be ~10-20 min; bottleneck is `generate_content` latency (~5-10s per video) not upload.
