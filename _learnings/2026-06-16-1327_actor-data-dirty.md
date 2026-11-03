# Actor data is dirty

*From LEARNINGS.md, section "Website MVP — frontend & deploy (2026-06-16)".*

**Actor data is dirty:** 203 distinct raw `main_actors` strings for ~10 real actors (mixed comma/space separators, typos like `Հակյո`→`Հայկո`, `ՄԿո`→`Մկո`, role-words like `ոստիկան` mixed in, and `Ոչ մի` = "nobody" placeholders). Canonicalize by comma-split-first (space-split only when there's no comma, so `փոքր երեխա` isn't torn apart) against a small known-actor allowlist; route non-actors to `rolesNames`.
