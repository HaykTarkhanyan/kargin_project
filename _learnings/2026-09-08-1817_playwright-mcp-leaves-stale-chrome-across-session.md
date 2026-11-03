# Playwright MCP leaves a stale Chrome across session restarts

*From LEARNINGS.md, section "2026-09-08 — custom-domain plumbing".*

**Playwright MCP leaves a stale Chrome across session restarts** ("Browser is already in use … mcp-chrome-…"): kill `chrome.exe` processes whose CommandLine contains `ms-playwright-mcp` and reconnect. Site login sessions (name.am, Google) survive in the persistent profile.
