# GitHub Pages deployed via Actions serves the artifact as-is — no Jekyll runs

*From LEARNINGS.md, section "Website MVP — frontend & deploy (2026-06-16)".*

**GitHub Pages deployed via Actions serves the artifact as-is — no Jekyll runs**, so `.nojekyll` is belt-and-suspenders, not strictly required. Enable Pages headless with `gh api -X POST repos/OWNER/REPO/pages -f build_type=workflow`; the deploy job 404s ("Ensure GitHub Pages has been enabled") until it's on. The build job runs and validates the whole pipeline even before Pages is enabled.
