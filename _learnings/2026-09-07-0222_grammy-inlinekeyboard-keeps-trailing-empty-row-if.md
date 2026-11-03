# grammY `InlineKeyboard` keeps a trailing empty row if you end with `.row()`

*From LEARNINGS.md, section "2026-09-07 — Telegram bot: live operation and UX mechanics".*

**grammY `InlineKeyboard` keeps a trailing empty row if you end with `.row()`**, and conditional buttons can strand a `kb.row()` with nothing after it. Call `.row()` only BETWEEN buttons, and when buttons are conditional, collect the survivors first and only then lay out rows.
