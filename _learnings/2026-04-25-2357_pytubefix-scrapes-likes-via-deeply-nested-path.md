# `pytubefix` scrapes likes via a deeply nested path

*From LEARNINGS.md, section "From the original (pre-rewrite) codebase".*

**`pytubefix` scrapes likes via a deeply nested path** (`yt.initial_data['videoPrimaryInfoRenderer']...`). This breaks whenever YouTube changes its page structure. Any rewrite that depends on like counts needs a more durable source (official API or accept-it-might-be-missing).
