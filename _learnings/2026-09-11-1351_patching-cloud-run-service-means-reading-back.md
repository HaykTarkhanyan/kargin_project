# Patching a Cloud Run service means reading it back and re-sending it

*From LEARNINGS.md, section "2026-09-11 — deploying Cloud Run without a local container build".*

**Patching a Cloud Run service means reading it back and re-sending it.** The v2 API takes the whole object, so a PATCH must drop the server-managed fields (`uid`, `etag`, `conditions`, `latestReadyRevision`, `terminalCondition`, `urls`, …) and `template.revision`, or it is rejected or pins the revision name. Env vars survive because they live in `template` and are echoed back untouched — verified after deploy rather than assumed, since silently losing `BOT_TOKEN` would take the bot down.
