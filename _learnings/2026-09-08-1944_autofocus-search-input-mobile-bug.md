# `autoFocus` on a search input is a mobile bug

*From LEARNINGS.md, section "2026-09-08 — mobile: nested scroll containers are the whole problem".*

**`autoFocus` on a search input is a mobile bug.** It opens the keyboard on load, hiding the results the visitor came for. Gate it: `window.matchMedia("(min-width: 1024px) and (pointer: fine)")`. Keep the input at >=16px font (17px here) or iOS Safari zooms the page on focus. Autofocus is still right on a single-purpose page like `/find-my-name`, where the keyboard is the point and there is nothing to cover.
