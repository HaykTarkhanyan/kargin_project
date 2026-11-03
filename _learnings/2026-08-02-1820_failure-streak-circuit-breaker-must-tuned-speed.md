# A failure-streak circuit breaker must be tuned to the SPEED of the expected failure, not just the count

*From LEARNINGS.md, section "Batch transcription, and how the Shazam throttle actually behaves (2026-08-02)".*

**A failure-streak circuit breaker must be tuned to the SPEED of the expected failure, not just the count.** The limit of 15 was chosen for a dropped wifi link, where each failure is an instant DNS error and the whole streak is free. Under a throttle each failure burns the full 45 s timeout, so the same threshold cost ~15 minutes of dead waiting per round (21 failures) between ~12 minutes of productive work and the cooldown. Dropping it to 4 cut that to ~3 minutes and is *strictly gentler* on the remote service — fewer requests while already blocked. The productive window is ~12 minutes either way, which is what suggests a budget per window rather than a per-request rate limit.
