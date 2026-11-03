# Bug at `old/pages/1_Search_Episodes.py:349`

*From LEARNINGS.md, section "From the original (pre-rewrite) codebase".*

**Bug at `old/pages/1_Search_Episodes.py:349`**: `is_fuzzy=(search_type == "Fuzzy Search")` — but radio values are `"Simple Fuzzy"`/`"Advanced Fuzzy"`, so highlight always falls through to exact-match branch. Fuzzy highlights never render.
