# The Worker+Neon logging stack was never live

*From LEARNINGS.md, section "2026-09-06 — Firebase migration (phase 1-3 code)".*

**The Worker+Neon logging stack was never live.** `gh variable list` is empty — `LOG_ENDPOINT` was never set, so the site never sent an event and there is nothing to soak/export before decommissioning. The dormant-since-June stack moved to `old/logger-worker/` untested in production.
