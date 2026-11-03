# Logging from a static site needs an external endpoint, and `sendBeacon` must use `text/plain`

*From LEARNINGS.md, section "Website v2 — EDA, discovery, layout (2026-06-16)".*

**Logging from a static site needs an external endpoint, and `sendBeacon` must use `text/plain`.** GitHub Pages can't hold a DB credential, so events POST to a tiny Cloudflare Worker that inserts into Neon (`DATABASE_URL` is a Worker secret). Two gotchas: (1) `navigator.sendBeacon` with an `application/json` Blob triggers a CORS preflight it can't perform → send the body as a **`text/plain` Blob** (CORS-safelisted) and `JSON.parse` it on the worker; (2) insert a jsonb column with an explicit `::jsonb` cast on the param, or Postgres errors "column is jsonb but expression is text". Ship logging **dormant** (no-op until an env var sets the endpoint) so it's decoupled from provisioning the backend.
