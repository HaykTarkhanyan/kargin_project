# An empty `match` block is a firestore.rules compile error

*From LEARNINGS.md, section "2026-09-06 — Firebase migration (phase 1-3 code)".*

**An empty `match` block is a firestore.rules compile error.** `match /databases/{db}/documents { }` fails `initializeTestEnvironment` with an unhelpful downstream `env.cleanup` TypeError. A deny-all placeholder needs an explicit `match /{document=**} { allow read, write: if false; }` even though deny is already the default.
