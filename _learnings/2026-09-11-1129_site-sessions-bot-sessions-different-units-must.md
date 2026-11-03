# Site "sessions" and bot "sessions" are different units and must never be summed

*From LEARNINGS.md, section "2026-09-11 — the prefetch 404s were a local-serving ghost, and what usage data says".*

**Site "sessions" and bot "sessions" are different units and must never be summed.** The site's `sessionId` is a `sessionStorage` UUID — new per tab, per browser restart. The bot's is a truncated sha256 of the Telegram user id — stable forever. 50 site "visits" vs 1 bot "user" are not comparable numbers.
