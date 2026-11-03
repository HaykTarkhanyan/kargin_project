# Contact sheets: Claude vision cost is set by sheet AREA, not tile count

*From LEARNINGS.md, section "2026-09-03 — 360p corpus, contact sheets, visual annotations".*

**Contact sheets: Claude vision cost is set by sheet AREA, not tile count.** The current formula is ceil(w/28)*ceil(h/28) tokens (28 px patches; the old pixels/750 rule is obsolete). Fable/Opus-tier accepts 2576 px long edge / 4784 tokens without downscaling, so an 8x5 grid of 320x180 tiles (2560x900) carries 40 frames for ~3.0k tokens — ~3x cheaper than the same coverage as loose frames. Verified in practice: a sketch's story is readable from one sheet (Jorik's towel/kolgotki gag was visible before the text confirmed it).
