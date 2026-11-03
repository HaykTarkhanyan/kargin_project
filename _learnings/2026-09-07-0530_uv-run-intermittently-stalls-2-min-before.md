# `uv run` intermittently stalls ~2 min before the script starts on this machine

*From LEARNINGS.md, section "2026-09-07 — Gemini extraction pilot (Vertex AI)".*

**`uv run` intermittently stalls ~2 min before the script starts on this machine** (three sightings today, incl. a plain cached-row skip); the same script via `.venv/Scripts/python.exe` starts instantly. For time-sensitive or chained commands, prefer the venv python directly.
