# When every record shares a title template, string similarity measures the template, not the record

*From LEARNINGS.md, section "Duplicate detection by audio fingerprint (2026-08-01)".*

**When every record shares a title template, string similarity measures the template, not the record.** Every row here is `Kargin Haghordum sketch NNN (Hayko Mko)`, so `SequenceMatcher` scores ~0.95 between *any* two rows — the only discriminating characters are 3 digits. A naive title-similarity filter returned hundreds of "matches". Worse, titles are unreliable in both directions: the 8 rows that share a title exactly are **different** sketches (188s vs 88s, 1% dialogue overlap), and the pair with identical curated dialogue has **different** titles. Duration alone is no better — 162 groups collide by coincidence at a 174s median across 702 clips. Textual metadata could confirm exactly **1** duplicate; audio found **23**.
