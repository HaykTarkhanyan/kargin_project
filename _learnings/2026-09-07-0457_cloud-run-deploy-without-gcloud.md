# Cloud Run deploy without gcloud

*From LEARNINGS.md, section "2026-09-07 — Cloud Run's reserved /healthz path".*

**Cloud Run deploy without gcloud**: local docker build (daemon is linux/amd64 ✓) → `docker login -u oauth2accesstoken --password-stdin` to Artifact Registry → REST v2 services create/PATCH with the firebase-CLI-token trick. Deterministic URL `https://<svc>-<projectnumber>.<region>.run.app` works and can be baked into env before the first deploy (self-registering webhook needs it).
