# Auditing "can this bill me?" beats promising it won't

*From LEARNINGS.md, section "2026-09-07 — Cloud Run's reserved /healthz path".*

**Auditing "can this bill me?" beats promising it won't.** The decisive artifacts: `serviceusage list ENABLED` (compute/run/functions/container absent = no VM can exist), App Engine `GET /apps/<project>` 404 (enabled API but no app = cannot bill), budget GET (alert rules verified, not assumed). Also recorded plainly: **GCP budgets only notify — a true spending cap does not exist on Blaze**; the billing-detach kill-switch exists but takes the site down, rejected at this scale.
