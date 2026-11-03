# Inline results are cached ~`cache_time` per exact query string

*From LEARNINGS.md, section "2026-09-07 — Telegram bot: live operation and UX mechanics".*

**Inline results are cached ~`cache_time` per exact query string** (we set 300 s). When iterating on the card format, an identical inline query shows the OLD render — vary the query while testing, don't debug a "stale" card.
