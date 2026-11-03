# Audio input tokens are model-independent

*From LEARNINGS.md, section "Gemini STT spike (2026-04-26)".*

**Audio input tokens are model-independent.** Same 26,703 input tokens whether you call Lite or Pro on the same audio. So `tokens_in × per-model rate` is the cost-comparison formula. You can pre-compute audio tokens once and cost-rank every model.
