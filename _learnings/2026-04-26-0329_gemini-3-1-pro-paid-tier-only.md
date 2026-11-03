# Gemini 3.1 Pro is paid-tier-only

*From LEARNINGS.md, section "Gemini STT spike (2026-04-26)".*

**Gemini 3.1 Pro is paid-tier-only** — free-tier requests return 429 immediately with `limit: 0` for all Pro metrics. The 429 fails before upload happens, so probing for "is this model accessible on my tier?" costs nothing. To use Pro, link a billing account via aistudio.google.com → project → Billing.
