# MiniSearch cannot do mid-word substring search

*From LEARNINGS.md, section "Website MVP — frontend & deploy (2026-06-16)".*

**MiniSearch cannot do mid-word substring search.** Its tokenizer splits on whitespace/punctuation and keeps whole tokens, so a pasted mid-quote fragment matches nothing — fatal for quote search. For a small corpus (702 rows) a normalized in-memory `.includes()` scan is simpler, gives true substring, and is sub-millisecond. Don't reach for a search lib reflexively at this scale.
