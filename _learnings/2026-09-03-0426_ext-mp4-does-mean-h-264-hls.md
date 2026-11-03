# `ext=mp4` does NOT mean H.264, and HLS downloads can truncate silently

*From LEARNINGS.md, section "2026-09-03 — 360p corpus, contact sheets, visual annotations".*

**`ext=mp4` does NOT mean H.264, and HLS downloads can truncate silently.** YouTube lists VP9-in-mp4 renditions served over m3u8; `bestvideo[ext=mp4]` picked one (fmt 605 at 567k outranked healthy avc1 134 at 508k) and the download produced 42 s of video against 143 s of audio with exit code 0. Pin `vcodec^=avc1` + `protocol=https`. Detection: compare video vs audio STREAM durations with ffprobe (>2 s apart = broken); container duration lies — it reports the longer stream.
