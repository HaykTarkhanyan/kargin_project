# Killing `-webkit-tap-highlight-color` without a replacement makes taps feel dead

*From LEARNINGS.md, section "2026-09-08 — mobile: nested scroll containers are the whole problem".*

**Killing `-webkit-tap-highlight-color` without a replacement makes taps feel dead.** Pair it with `@media (hover:none){ a:active,button:active{opacity:.6} }` so touch keeps its feedback and mice never see it.
