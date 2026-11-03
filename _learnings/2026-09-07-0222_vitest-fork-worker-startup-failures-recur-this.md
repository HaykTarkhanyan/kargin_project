# Vitest fork-worker startup failures recur on this laptop under load, not just after npm installs

*From LEARNINGS.md, section "2026-09-07 — Telegram bot: live operation and UX mechanics".*

**Vitest fork-worker startup failures recur on this laptop under load, not just after npm installs** (second sighting: "Failed to start forks worker" for 2 of 12 files while the bot's vitest ran concurrently; clean rerun passed 81/81). Rule stands: rerun once before debugging a mass test failure with ~0ms of actual test time.
