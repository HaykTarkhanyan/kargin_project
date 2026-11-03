# Gemini reliably ignores foreign-language song intros when prompted explicitly

*From LEARNINGS.md, section "Gemini STT spike (2026-04-26)".*

**Gemini reliably ignores foreign-language song intros when prompted explicitly.** All 3 confounder videos (where YouTube STT was fooled into Romanian/Turkish/Spanish garbage by the song intro) produced correct Armenian transcripts. The working prompt names the failure mode directly: "The video may open with a Russian or Spanish song before the dialogue starts; skip it and only transcribe the spoken Armenian dialogue." Generic "transcribe Armenian speech" without naming the song-intro problem might also work; not tested.
