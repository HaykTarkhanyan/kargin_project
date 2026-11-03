# JSON3 has a lot of presentation cruft

*From LEARNINGS.md, section "YouTube transcript fetch (2026-04-26)".*

**JSON3 has a lot of presentation cruft** (`pens`, `wsWinStyles`, `wpWinPositions`, plus per-event `wpWinPosId`/`wsWinStyleId`/`wWinId`/`id`). Strip it for any downstream use. Empty cue-only events without `segs` should also be dropped — they contribute nothing to text content. Useful info lives in `events[].segs[].utf8` plus `tStartMs`/`dDurationMs` (in milliseconds; convert to seconds for consistency with `data/youtube_metadata.csv`).
