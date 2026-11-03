# Low memory disguises itself as test failures, and the messages are convincing

*From LEARNINGS.md, section "2026-09-12 — collections, and four things that looked like bugs but were not".*

**Low memory disguises itself as test failures, and the messages are convincing.** With 0.3 GB free, `vitest` reported `Error: [vitest-pool-runner]: Timeout waiting for worker to respond` on 6 of 15 files, and `npm run test:rules` printed `19 skipped` with exit 1 — which reads as a rules regression but is the emulator connection failing in `beforeAll`. The same commit passed everything after a restart: 102 python, 127 web, 19 rules. Check free memory before debugging a test suite that was green an hour ago.
