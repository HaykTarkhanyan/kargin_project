# Next dev 500s on URL-encoded non-ASCII dynamic params under `output: export`

*From LEARNINGS.md, section "2026-09-08 — mobile: nested scroll containers are the whole problem".*

**Next dev 500s on URL-encoded non-ASCII dynamic params under `output: export`** — `/actor/%D5%80...` dies with *"missing param in generateStaticParams()"* while `npm run build` exports all 13 actor pages happily. Verify these routes against the built `out/` (a plain `python -m http.server` there is enough), not the dev server. That static server also holds a lock on `out/`, so stop it before rebuilding or the build fails with `EBUSY: rmdir`.
