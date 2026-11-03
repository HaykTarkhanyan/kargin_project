# Express such thresholds as fractions of `log(N)`, never absolute numbers

*From LEARNINGS.md, section "2026-09-11 — fixing phrase search: what the measurements overturned".*

**Express such thresholds as fractions of `log(N)`, never absolute numbers.** Tuned against 702 sketches, they read 1.2 / 2.5 / 4.5 — and silently disabled the whole pass on the 2-3 sketch datasets the unit tests use, because word weights scale with corpus size. Three tests failed in a way that looked like a logic bug and was a units bug.
