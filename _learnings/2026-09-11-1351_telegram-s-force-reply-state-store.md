# Telegram's `force_reply` is a state store

*From LEARNINGS.md, section "2026-09-11 — deploying Cloud Run without a local container build".*

**Telegram's `force_reply` is a state store.** A bot on scale-to-zero cannot remember that someone is mid-report between two updates. Sending the prompt with `force_reply` makes the user's reply carry the prompt text back in `reply_to_message`, so the bot recognises it by the prompt's first character and reads the failed query straight out of the rendered text. No database, no session, nothing to expire. Worth remembering: Telegram hands back the **rendered** message, so a parser must match what a person sees, not the HTML that produced it.
