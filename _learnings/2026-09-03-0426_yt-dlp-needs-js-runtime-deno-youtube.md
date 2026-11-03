# yt-dlp needs a JS runtime (deno) for YouTube since mid-2026

*From LEARNINGS.md, section "2026-09-03 — 360p corpus, contact sheets, visual annotations".*

**yt-dlp needs a JS runtime (deno) for YouTube since mid-2026.** Our pinned 2026.3.17 got `HTTP Error 403` on a 720p DASH stream with the warning "No supported JavaScript runtime could be found". Fix: pin the current release AND install deno; without both, formats silently go missing or 403.
