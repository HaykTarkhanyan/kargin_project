# Enabling inline mode in BotFather needs no bot restart

*From LEARNINGS.md, section "2026-09-07 — Telegram bot: live operation and UX mechanics".*

**Enabling inline mode in BotFather needs no bot restart** — `inline_query` updates are in the default `getUpdates` delivery, so a handler registered at boot starts firing the moment `/setinline` flips. Verify with `getMe` → `supports_inline_queries`.
