# `PYTHONIOENCODING=utf-8` is required

*From LEARNINGS.md, section "Gemini STT spike (2026-04-26)".*

**`PYTHONIOENCODING=utf-8` is required** to print Armenian text in Git Bash on Windows. Default cp1252 charmap raises UnicodeEncodeError on the first Armenian glyph. Set as env var before invoking Python; doesn't affect file I/O which is always controlled via the `encoding="utf-8"` arg.
