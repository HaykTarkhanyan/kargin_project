# "Gemini 3.1 Flash" is no longer a single model

*From LEARNINGS.md, section "Gemini STT spike (2026-04-26)".*

**"Gemini 3.1 Flash" is no longer a single model.** In 3.1 the Flash family split into Lite (`gemini-3.1-flash-lite-preview`, batch STT, "fast and at scale", free on free tier), Live (`gemini-3.1-flash-live-preview`, real-time bidirectional voice, paid per minute), and TTS (`gemini-3.1-flash-tts-preview`, output-only). For batch transcription of stored audio files, **Lite** is the right model id; Live is 6x more expensive per audio-input token and is overkill for non-streaming work.
