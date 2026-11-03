# Telegram's 64-byte `callback_data` cap is BYTES, and Armenian is 2 bytes/char

*From LEARNINGS.md, section "2026-09-07 — Telegram bot: live operation and UX mechanics".*

**Telegram's 64-byte `callback_data` cap is BYTES, and Armenian is 2 bytes/char.** Encoding facet VALUES into callbacks blows the budget instantly («Հիվանդանոց» alone is 20 bytes); encode INDEXES into boot-derived lists instead, and pack the whole view state (`loc:actor:dur:offset:query`, query last so it may contain `:`) into every button so paging/filters/panels compose statelessly. Guard with a byte-length check that DROPS the button rather than truncating — truncated state decodes into a different query.
