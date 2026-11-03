# Disproven: the site does NOT have broken `<Link>` prefetching

*From LEARNINGS.md, section "2026-09-11 — the prefetch 404s were a local-serving ghost, and what usage data says".*

**Disproven: the site does NOT have broken `<Link>` prefetching.** I reported RSC prefetch 404s (`__next.sketch.$d$id.txt?_rsc=…`) as a real issue after seeing them while serving `web/out/` with `python -m http.server`. On the live site every one of them is a **200** — 66 prefetch requests on the Hayko actor page, zero failures. The export writes those payloads *nested* (`__next.sketch/$d$id.txt`) but the browser asks for them *flat* (`__next.sketch.$d$id.txt`); `firebase deploy` normalises the names on upload, a dumb static file server does not. **Never diagnose static-export routing from `python -m http.server`** — it lacks the host's path handling. Check the deployed URL before calling anything broken:
  ```powershell
  Invoke-WebRequest "https://<host>/sketch/<id>/__next.sketch.`$d`$id.txt" -UseBasicParsing   # 200 on Firebase
  ```
