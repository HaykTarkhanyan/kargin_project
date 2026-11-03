# The firebase CLI's stored credential can drive ANY Google REST API

*From LEARNINGS.md, section "2026-09-07 — driving GCP without gcloud".*

**The firebase CLI's stored credential can drive ANY Google REST API.** Exchange `~/.config/configstore/firebase-tools.json`'s refresh_token using the CLI's public installed-app client (id + secret are shipped constants in `firebase-tools/lib/api.js`) at `oauth2.googleapis.com/token`, then Bearer-call serviceusage/cloudbilling/billingbudgets/IAM as the logged-in user. Replaced gcloud entirely for: enabling APIs, linking billing, creating budgets, granting roles, minting SA keys. Keep tokens out of stdout; write keys straight to gitignored files.
