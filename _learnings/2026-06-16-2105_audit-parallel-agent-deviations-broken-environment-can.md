# Audit parallel-agent deviations — a broken environment can make an agent "fix" the wrong thing

*From LEARNINGS.md, section "Website v2 — EDA, discovery, layout (2026-06-16)".*

**Audit parallel-agent deviations — a broken environment can make an agent "fix" the wrong thing.** Two worktree agents each ran `npm ci`, filling the disk to 100%; one got a corrupt `next` install, concluded "the type check is broken," and slipped `typescript:{ignoreBuildErrors:true}` into next.config (disabling type-checking site-wide). The real fix was reinstalling. Lesson: when an agent reports a "pre-existing framework bug" that contradicts known-green history, suspect its environment, and re-verify any global escape-hatch it added against a clean build before merging. Also: N parallel worktrees = N full `node_modules` — real disk pressure on a constrained machine; prune worktrees promptly.
