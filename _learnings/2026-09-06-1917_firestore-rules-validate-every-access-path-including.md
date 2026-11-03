# Firestore rules validate every access path, including raw REST

*From LEARNINGS.md, section "2026-09-06 — Firebase migration (phase 1-3 code)".*

**Firestore rules validate every access path, including raw REST.** The events transport is a plain `fetch(keepalive)` POST to `documents:commit` with zero SDK bytes — rules still gate it, and `updateTransforms: setToServerValue REQUEST_TIME` satisfies a `ts == request.time` rule. Client clamps mirror the rules because a commit batch is atomic: one out-of-contract event would reject the whole batch.
