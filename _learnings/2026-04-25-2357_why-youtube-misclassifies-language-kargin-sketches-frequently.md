# Why YouTube misclassifies the language: Kargin sketches frequently open with a Russian or Spanish song as the soundtrack

*From LEARNINGS.md, section "From the metadata-fetch (2026-04-25)".*

**Why YouTube misclassifies the language: Kargin sketches frequently open with a Russian or Spanish song as the soundtrack** (per project owner). YouTube's language detector locks onto the song lyrics in the first few seconds and labels the whole video accordingly, even though the dialogue is Armenian. Two consequences for the transcription pipeline:
  1. Gemini STT will likely hit the same failure mode if fed full audio. Either prompt it to focus on speech and transcribe Armenian specifically, or segment out music first.
  2. The `auto_caption_source_lang` column is therefore an indirect signal of "what song is in the intro," not "what language the video is in." Could be useful for a soundtrack-detection feature but is not a reliable language label.
