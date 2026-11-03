# A Cloud Billing account has a project-link quota (5 by default) and the console fails SILENTLY on it

*From LEARNINGS.md, section "2026-09-07 — driving GCP without gcloud".*

**A Cloud Billing account has a project-link quota (5 by default) and the console fails SILENTLY on it.** The Firebase 'Link billing account' dialog just closed and stayed Spark; only the REST PUT surfaced 'Precondition check failed', and only the UI toast (user-side) named the quota. List victims via `billingAccounts/{id}/projects`, resolve display names via cloudresourcemanager — the opaque `gen-lang-client-*` AI Studio projects are indistinguishable without that.
