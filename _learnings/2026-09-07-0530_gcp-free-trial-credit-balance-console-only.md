# GCP free-trial credit balance is Console-only

*From LEARNINGS.md, section "2026-09-07 — Gemini extraction pilot (Vertex AI)".*

**GCP free-trial credit balance is Console-only** — no gcloud/REST surface exposes it (cloudbilling shows accounts, not credit remainders). ADC identity for this repo's Vertex calls: metric.am.academy@gmail.com, billing account 014ED9-E2C7D1-EA001F; deep-link `console.cloud.google.com/billing/<ACCOUNT>/credits?authuser=<email>` to skip the account-picker maze. The ADC token's email is recoverable via the oauth2 tokeninfo endpoint when nobody remembers which account authorized it.
