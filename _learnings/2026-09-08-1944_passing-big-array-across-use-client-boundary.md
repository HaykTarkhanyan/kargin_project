# Passing a big array across a `"use client"` boundary costs the whole array, rendered or not

*From LEARNINGS.md, section "2026-09-08 — mobile: nested scroll containers are the whole problem".*

**Passing a big array across a `"use client"` boundary costs the whole array, rendered or not.** Making `SketchGrid` a client component for a "load more" button *increased* nothing visibly but left the actor page at 2.2 MB — 2.1 MB of it inline `<script>`, the RSC payload with all 532 serialised sketches, even though only 48 cards were drawn. Slicing server-side instead and linking to search took it to 295 KB. Measure `([regex]::Matches($html,'(?s)<script[^>]*>.*?</script>') | Measure-Object -Property Length -Sum).Sum` before blaming the markup.
