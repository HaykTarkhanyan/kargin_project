# YouTube tags the source-language STT track with a `-orig` suffix

*From LEARNINGS.md, section "YouTube transcript fetch (2026-04-26)".*

**YouTube tags the source-language STT track with a `-orig` suffix** (e.g. `hy-orig`, `tr-orig`). The bare lang code (`hy`, `tr`) is the auto-translated derivative. This convention isn't part of yt-dlp's documented API contract, but it's stable across the current versions and is the only way to distinguish source from translation in the `automatic_captions` dict yt-dlp returns from `extract_info`.
