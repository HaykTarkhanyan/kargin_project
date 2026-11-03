# Concurrent agents sharing a scratchpad WILL clobber each other's helper scripts

*From LEARNINGS.md, section "2026-09-04 — Opus second pass, agent-fleet operations".*

**Concurrent agents sharing a scratchpad WILL clobber each other's helper scripts.** One agent's `crop.py` silently switched from 1-indexed to 0-indexed tiles between its own calls because a sibling agent rewrote the file mid-run. The victim caught it only because the burned-in timestamps contradicted the crops. Rule now in the skill: uniquely-named helper files per agent.
