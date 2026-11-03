# The bot must NOT run locally in polling mode while the Cloud Run webhook is set

*From LEARNINGS.md, section "2026-09-07 — Cloud Run's reserved /healthz path".*

**The bot must NOT run locally in polling mode while the Cloud Run webhook is set** — Telegram allows one delivery mode; local dev now requires `deleteWebhook` first (documented in bot/README.md).
