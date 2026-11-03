# Model self-reported confidence is dead weight

*From LEARNINGS.md, section "2026-09-07 — Gemini extraction pilot (Vertex AI)".*

**Model self-reported confidence is dead weight**: 30/32 pilot outputs said "high" regardless of input richness (title-only vs full transcript). Compute input-profile flags in code instead; only Sonnet ever said "medium".
