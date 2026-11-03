# Gemini's transcript is qualitatively cleaner than YouTube's hy-orig STT

*From LEARNINGS.md, section "Gemini STT spike (2026-04-26)".*

**Gemini's transcript is qualitatively cleaner than YouTube's hy-orig STT** even on videos where YouTube returned valid Armenian: full punctuation (question marks, periods), proper sentence boundaries, music omitted entirely (vs YouTube interleaving `[երաժշտություն]`), grammatically coherent even where individual words are misheard. YouTube's segmentation is more granular (~2x more events) because it segments on visual subtitle cues; Gemini segments at the clause/sentence level which is better for search.
