# Counting matched words equally does not work; weight them by rarity

*From LEARNINGS.md, section "2026-09-11 — fixing phrase search: what the measurements overturned".*

**Counting matched words equally does not work; weight them by rarity.** The first attempt required "most of the query's words" and returned **538 of 702** sketches for `պապա պտի ասես` — satisfied by "պտի" and "եմ" alone, ranked by nothing. Weighting each word by `log(N / sketches containing it)` and requiring a sketch to account for a share of the query's total puts the requirement on the words that carry meaning. A word in every sketch scores ~0 and cannot qualify anything; a word in six scores 4.8 and identifies a sketch by itself.
