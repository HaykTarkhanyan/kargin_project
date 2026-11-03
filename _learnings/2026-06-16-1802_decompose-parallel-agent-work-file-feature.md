# Decompose parallel-agent work by FILE, not by feature

*From LEARNINGS.md, section "Website v2 — EDA, discovery, layout (2026-06-16)".*

**Decompose parallel-agent work by FILE, not by feature.** "Romanized search" and "fuzzy search" are different *features* but both rewrite `search.ts`, so separate worktrees would just merge-conflict — they had to share one worktree; the mobile pass (CSS/components) was the only truly independent axis. Each fresh git worktree also needs its own `npm ci` (node_modules is gitignored), so N parallel worktrees = N installs + builds — real local load.
