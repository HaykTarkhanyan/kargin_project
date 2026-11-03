# When search starts matching differently, highlighting has to follow

*From LEARNINGS.md, section "2026-09-11 — fixing phrase search: what the measurements overturned".*

**When search starts matching differently, highlighting has to follow.** Phrase results initially rendered with zero `<mark>`s, because the highlighter still looked for the whole query as one substring — 28 results with no visible reason for any of them. Matching per word and merging the ranges fixed it, and then `matchedFirst` needed to rank by how much of the query a line covers, since with per-word matching nearly every line "matches".
