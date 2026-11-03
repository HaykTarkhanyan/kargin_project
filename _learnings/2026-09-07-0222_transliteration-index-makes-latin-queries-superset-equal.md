# The transliteration index makes Latin queries a SUPERSET, not an equal set

*From LEARNINGS.md, section "2026-09-07 — Telegram bot: live operation and UX mechanics".*

**The transliteration index makes Latin queries a SUPERSET, not an equal set.** `tormuz` matches more sketches than «տոռմուզ» because ո→o and ռ/ր→r collapse distinct Armenian words into one Latin form. Correct parity assertion: Armenian hits ⊆ Latin hits. (A bot test first asserted equality and failed against the real corpus.)
