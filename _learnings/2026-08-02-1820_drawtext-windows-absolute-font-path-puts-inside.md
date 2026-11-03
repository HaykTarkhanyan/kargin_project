# `drawtext` on Windows: an absolute font path puts a `:` inside the filter string

*From LEARNINGS.md, section "Batch transcription, and how the Shazam throttle actually behaves (2026-08-02)".*

**`drawtext` on Windows: an absolute font path puts a `:` inside the filter string**, where it parses as an option separator. Copy the font next to the work files and reference it relatively. Keep card text ASCII too — Armenian titles need escaping, and a mis-escaped title fails silently.
