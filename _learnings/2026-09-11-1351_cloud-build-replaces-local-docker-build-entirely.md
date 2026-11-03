# Cloud Build replaces the local docker build entirely, and the laptop never feels it

*From LEARNINGS.md, section "2026-09-11 — deploying Cloud Run without a local container build".*

**Cloud Build replaces the local docker build entirely, and the laptop never feels it.** `scripts/deploy_bot.py` tars only the paths `bot/Dockerfile` actually COPYs (807 KB, versus a repo root holding gigabytes of media), uploads to `gs://<project>_cloudbuild`, builds remotely and repoints the service. Whole round trip ~3 minutes with nothing running locally — no Docker Desktop, no gcloud, and no risk of freezing the machine the way the first local build did on 2026-09-07.
