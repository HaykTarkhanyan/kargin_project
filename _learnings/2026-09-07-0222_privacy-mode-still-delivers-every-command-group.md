# Privacy mode ON still delivers EVERY `/command` in a group — including ones aimed at other bots

*From LEARNINGS.md, section "2026-09-07 — Telegram bot: live operation and UX mechanics".*

**Privacy mode ON still delivers EVERY `/command` in a group — including ones aimed at other bots.** A text handler that answers unknown commands will publicly nag on `/cmd@OtherBot`. Gate free-text handling to `ctx.chat.type === "private"`; groups get own-commands + inline only. (Caught in review, was live for ~an hour.)
