# Fuzzy search: index WORDS, not whole strings

*From LEARNINGS.md, section "Website v2 — EDA, discovery, layout (2026-06-16)".*

**Fuzzy search: index WORDS, not whole strings.** A 1-char typo scored ~0.5 with Fuse.js against each sketch's full searchable string (above a 0.35 threshold → missed), but ~0.17 against **word-level** documents (one Fuse record per word). For short queries against long docs, the query-to-doc length ratio wrecks full-string fuzzy scoring; word-level fixes it.
