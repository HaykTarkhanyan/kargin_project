# Identifying the music ourselves beats asking YouTube

*From LEARNINGS.md, section "Squeezing copyright signal out of YouTube (2026-08-01)".*

**Identifying the music ourselves beats asking YouTube.** ShazamIO (unofficial, reverse-engineered, no API key) matched **27 of 39 clips across 6 videos**, and agreed exactly with YouTube's own panel on 3 of 4 where YouTube named a track (Pink Panther, Thriller, Avril Lavigne; on the fourth it returned ABBA *Dancing Queen* where YouTube claimed ABBA *Mamma Mia* — right artist, different track). It also found music YouTube never surfaced, including a blind hit on the one video blocked in **US/PR/AS/UM**: Ricchi & Poveri — *Sarà Perché Ti Amo* on **RCA (a Sony label)**, which explains a US-territory block that YouTube itself would not disclose. `recognize()` takes raw bytes, so clips pipe straight from ffmpeg with no temp files.
