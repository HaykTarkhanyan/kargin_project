# Memoize derived search text; don't recompute it per keystroke

*From LEARNINGS.md, section "Website v2 — EDA, discovery, layout (2026-06-16)".*

**Memoize derived search text; don't recompute it per keystroke.** The exact-match path was calling `romanize()` over every sketch's full dialogue on each keystroke (702× per character) — invisible at first, but adding a second transliteration (Cyrillic) would double it. Cache the combined searchable string per sketch in a `WeakMap` keyed by the sketch *object* (safe even if two sketches share an id, unlike an id-keyed Map). Transliteration then runs once, not on every input event. Multi-script search = index all forms (Armenian + Latin + Cyrillic) into one string and match the raw query against it; never transliterate the query or detect its script.
