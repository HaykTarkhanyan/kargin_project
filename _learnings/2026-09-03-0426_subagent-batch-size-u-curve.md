# Subagent batch size is a U-curve

*From LEARNINGS.md, section "2026-09-03 — 360p corpus, contact sheets, visual annotations".*

**Subagent batch size is a U-curve.** Fixed overhead amortizes (saturating — cache re-reads are a constant tax) while per-sheet context accumulation grows linearly; the bottom is ~9-12 items per agent. Measured: 17k tokens/sheet at 5/agent vs ~11k at 9/agent. Launch waves, not all at once, so the shared prompt prefix caches instead of racing.
