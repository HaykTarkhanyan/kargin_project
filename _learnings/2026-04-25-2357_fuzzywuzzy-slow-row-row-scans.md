# `fuzzywuzzy` is slow on row-by-row scans

*From LEARNINGS.md, section "From the original (pre-rewrite) codebase".*

**`fuzzywuzzy` is slow on row-by-row scans** — the Telegram bot iterates the entire DataFrame for every text search. Fine at a few hundred rows; would not scale.
