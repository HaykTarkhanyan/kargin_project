# Romanized search = index both forms, don't transliterate the query

*From LEARNINGS.md, section "Website v2 — EDA, discovery, layout (2026-06-16)".*

**Romanized search = index both forms, don't transliterate the query.** Append `romanize(armenianText)` to each doc's searchable string and match the raw normalized query against the combined text: a Latin query (`tormuz`) hits the romanized part, an Armenian query hits the Armenian part — no query-side transliteration, no language detection. Cheap and symmetric. (Phonetic Eastern-Armenian map; handle the `ու`→`u` digraph before single chars.)
