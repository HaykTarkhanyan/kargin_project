# Google's frontend reserves z-suffixed paths (`/healthz`) on run.app URLs and answers them with its own branded 404 — the request NEVER...

*From LEARNINGS.md, section "2026-09-07 — Cloud Run's reserved /healthz path".*

**Google's frontend reserves z-suffixed paths (`/healthz`) on run.app URLs and answers them with its own branded 404 — the request NEVER reaches the container.** Symptoms are maddening: service Ready, IAM correct, ingress ALL, zero request logs, yet every probe 404s. Diagnosis keys: Google's 404 is ~1.5KB of HTML while an app 404 is small; a request that reaches Cloud Run carries `x-cloud-trace-context`. Fix: name the endpoint `/health`. Found via a forum thread with identical symptoms after ~20 min of dead-end config checking — the deploy had been working the whole time; only the probe path was cursed.
