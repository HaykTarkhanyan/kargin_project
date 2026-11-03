# A brand-new project has almost every API disabled

*From LEARNINGS.md, section "2026-09-07 — driving GCP without gcloud".*

**A brand-new project has almost every API disabled.** `firestore:databases:create` 403s until `firestore.googleapis.com` is enabled via serviceusage, and enablement takes ~1-2 min to propagate — retry in a loop, don't trust the first 403 after enabling.
