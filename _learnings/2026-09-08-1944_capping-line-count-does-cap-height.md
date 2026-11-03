# Capping by line count does not cap height

*From LEARNINGS.md, section "2026-09-08 — mobile: nested scroll containers are the whole problem".*

**Capping by line count does not cap height.** After slicing to 5 dialogue lines, cards still rendered 2,536px tall. Cause: `lib/segments.ts` split on `;` and `։` only, but machine transcripts separate lines with `\n`, so a whole transcript came back as two or three enormous "lines". Two lessons: a text cap needs a *pixel* bound as well (`max-h-* overflow-hidden` + a mask fade, so the cut looks deliberate), and a splitter written for one text source will silently mis-handle the second source someone later passes to it.
