# Rendering all 702 result cards at once is genuinely heavy

*From LEARNINGS.md, section "Website MVP — frontend & deploy (2026-06-16)".*

**Rendering all 702 result cards at once is genuinely heavy** — 702 DOM nodes each firing an external `img.youtube.com` request stalls first paint (even a Playwright screenshot timed out at 5s). Fix: cap initial render (~48 + a "load more" button) and use `<img loading="lazy">` (CSS `background-image` does NOT lazy-load). This only surfaced by running the real build in a browser — every unit test was green and the build succeeded.
