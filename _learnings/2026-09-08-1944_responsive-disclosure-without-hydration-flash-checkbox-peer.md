# Responsive disclosure without a hydration flash: checkbox + `peer`, not `useState`

*From LEARNINGS.md, section "2026-09-08 — mobile: nested scroll containers are the whole problem".*

**Responsive disclosure without a hydration flash: checkbox + `peer`, not `useState`.** `<input type="checkbox" class="peer sr-only">` + `hidden peer-checked:block lg:block` gives collapsed-on-phone / always-open-on-desktop in pure CSS, so the collapsed state *is* the server markup. A `useState`+`matchMedia` version renders one way then corrects itself. Gotcha: `peer-checked:` is a *sibling* combinator — it cannot reach a span nested inside the label. Use an arbitrary descendant variant on the sibling itself (`peer-checked:[&_[data-chev]]:rotate-180`).
