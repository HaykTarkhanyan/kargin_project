# Coverage limit worth remembering

*From LEARNINGS.md, section "Duplicate detection by audio fingerprint (2026-08-01)".*

**Coverage limit worth remembering:** fingerprints cover only the first 60 s of each file, so this finds pairs overlapping near the *start* of both. A compilation including a sketch eight minutes in is invisible. Only 31 videos exceed 300 s, so a full-length sliding search over just those would close the gap cheaply.
