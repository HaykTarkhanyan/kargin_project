# A nav item is not free, and the arithmetic is knowable before it breaks

*From LEARNINGS.md, section "2026-09-12 — collections, and four things that looked like bugs but were not".*

**A nav item is not free, and the arithmetic is knowable before it breaks.** Eleven Armenian labels need 1052 px at `gap-3.5`, which put the header's content at 1313 px. A 1280 px window has only 1265 px of layout width once the scrollbar is out — and Chrome's media queries measure the *window* (so `xl:` matched) while layout gets the narrower box. Result: 33 px of sideways scroll on every page between 1280 and about 1312, invisible at 1366 where it was first eyeballed. `gap-2` at `xl` with `2xl:gap-3.5` took the bar to 992 px and the overflow to 0. Measure `document.documentElement.scrollWidth - window.innerWidth` at the breakpoint itself, not above it.
