# Docker Desktop startup + a first image build can freeze this laptop

*From LEARNINGS.md, section "2026-09-07 — Cloud Run's reserved /healthz path".*

**Docker Desktop startup + a first image build can freeze this laptop** — it pulls the base image and runs two `npm ci` stages. That's ask-first territory per the global heavy-compute rule (violated once, user felt it). Subsequent builds are layer-cached and cheap.
