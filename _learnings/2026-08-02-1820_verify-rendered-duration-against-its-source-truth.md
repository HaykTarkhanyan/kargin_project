# Verify a rendered duration against its source of truth before shipping it

*From LEARNINGS.md, section "Batch transcription, and how the Shazam throttle actually behaves (2026-08-02)".*

**Verify a rendered duration against its source of truth before shipping it.** The drift above was caught only by an explicit check comparing the muxed output against the manifest total. Without it the video would have uploaded looking fine, and the error would have surfaced as an ID card that no longer matched the audio — after the ASR turnaround.
