# Multi-model output namespacing pattern

*From LEARNINGS.md, section "Gemini STT spike (2026-04-26)".*

**Multi-model output namespacing pattern**: `{seq:03d}_{video_id}__{model_short}.json` (double underscore as separator) lets multiple model runs coexist in one directory. Comparison renderer globs `spike_summary__*.json` to auto-discover available models — no list to maintain. Migration of existing single-model outputs is just a rename loop.
