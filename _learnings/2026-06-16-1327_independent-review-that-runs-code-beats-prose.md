# Independent review that *runs the code* beats prose review

*From LEARNINGS.md, section "Website MVP — frontend & deploy (2026-06-16)".*

**Independent review that *runs the code* beats prose review.** Two adversarial passes (spec, then plan) each caught real bugs only because the reviewer executed/inspected against real data: a `random` sort that returned input order unchanged (untested), a fabricated `title` when a fully-populated `titles` column existed, and the Tailwind-v4 config-file error. "Tests pass + build green" ≠ correct, and ≠ good-at-scale.
