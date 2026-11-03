# A single global correlation can't distinguish "uniformly degraded copy" from "identical for 80%, unrelated for the rest" — both land...

*From LEARNINGS.md, section "Duplicate detection by audio fingerprint (2026-08-01)".*

**A single global correlation can't distinguish "uniformly degraded copy" from "identical for 80%, unrelated for the rest" — both land mid-range.** Walk the aligned overlap in 10 s windows and report the fraction that correlate. That turned an opaque `corr=0.664` into "75% overlap, differs only in the first 20 s", and revealed the `partial` bucket is really *segment reuse* (recurring gags/stings shared across sketches: one pair shares 30 s at a **-82.6 s** lag).
