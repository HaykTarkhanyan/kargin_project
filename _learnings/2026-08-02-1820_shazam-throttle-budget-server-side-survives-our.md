# The Shazam throttle budget is server-side and survives our process dying

*From LEARNINGS.md, section "Batch transcription, and how the Shazam throttle actually behaves (2026-08-02)".*

**The Shazam throttle budget is server-side and survives our process dying.** A run that is killed externally at minute 10 of a ~12-minute productive window has already spent the budget; relaunching immediately walks straight into 45 s timeouts. So "the last run ended without errors" says nothing about whether it is safe to resume — the *only* reliable signal is a probe (3 sequential recognitions). Measured: a run killed at 157 clips with **zero errors** was followed by a relaunch whose very first clip timed out, and a probe then returned 0/3. Probe regardless of how the previous run ended.
