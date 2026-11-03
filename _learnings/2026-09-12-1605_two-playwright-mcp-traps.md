# Two Playwright MCP traps

*From LEARNINGS.md, section "2026-09-12 — collections, and four things that looked like bugs but were not".*

**Two Playwright MCP traps.** After `/mcp` reconnects, the previous browser still holds its profile lock and every call fails with `Browser is already in use ... use --isolated`; killing only the `chrome.exe` processes whose command line contains `ms-playwright-mcp` clears it and leaves the user's own Chrome alone (12 stale processes, 1.5 GB, versus 26 of theirs untouched). And `browser_take_screenshot` has a fixed 5 s budget that a 48-card page exceeds even after fonts load — `browser_run_code_unsafe` with `page.screenshot({ timeout: 30000 })` is the way to get the picture. The pictures were worth it: they are what showed the unhearted heart is a white emoji on a near-white circle, which no DOM assertion would have caught.
