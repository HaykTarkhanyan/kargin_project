# "Same audio" is not one relation — classify it by duration

*From LEARNINGS.md, section "Duplicate detection by audio fingerprint (2026-08-01)".*

**"Same audio" is not one relation — classify it by duration.** A 877s upload correlating at 0.995 with a 268s one is a **compilation containing** the sketch, not a duplicate. Splitting on `|dur_a - dur_b| <= 10s` gives `duplicate` vs `contains`. Without that split, 4 compilation pairs would have been written into `duplicate_of` as if they were re-uploads.
