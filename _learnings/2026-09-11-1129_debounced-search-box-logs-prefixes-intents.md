# A debounced search box logs prefixes, not intents

*From LEARNINGS.md, section "2026-09-11 — the prefetch 404s were a local-serving ghost, and what usage data says".*

**A debounced search box logs prefixes, not intents.** `web/lib/log.ts` fires after a 180 ms typing pause, so one person hunting one line produced `բո → բու → բուդ → բուդելնիկ → բուդելնիկն ա → …` as seven separate "searches". Raw counts (61 searches, 56 distinct queries) therefore overstate activity by roughly 4-5x; the honest unit is the longest query in a run. Anything built on this data should collapse prefix chains per session before counting, or log on submit/blur instead.
