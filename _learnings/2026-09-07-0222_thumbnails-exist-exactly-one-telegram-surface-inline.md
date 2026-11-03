# Thumbnails exist in exactly one Telegram surface: inline results

*From LEARNINGS.md, section "2026-09-07 — Telegram bot: live operation and UX mechanics".*

**Thumbnails exist in exactly one Telegram surface: inline results.** Keyboard buttons and message lines can't hold images, and a message renders only one link preview. The bridge: a `switch_inline_query_current_chat` button on the text-results message flips the same query into the inline list with real thumbnails; `switch_inline_query` (without `_current_chat`) opens the chat picker — that's the share button.
