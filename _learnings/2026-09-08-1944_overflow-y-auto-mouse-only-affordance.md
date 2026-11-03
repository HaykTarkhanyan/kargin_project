# `overflow-y-auto` is a mouse-only affordance

*From LEARNINGS.md, section "2026-09-08 — mobile: nested scroll containers are the whole problem".*

**`overflow-y-auto` is a mouse-only affordance.** With a wheel it is harmless; on touch the *same* drag gesture means both "scroll the page" and "scroll this box", and the browser awards it to whatever is under the thumb. The home page had **48** such boxes — one per card, 144px tall holding up to 5,271px of transcript — so on a phone most swipes landed in a trap. This was the user-reported "scrolling scrolls the description instead of the page". The fix is deleting the scroller, not tuning `touch-action`/`overscroll-behavior`: a 144px window onto 36 screenfuls was never a reading surface, and the card links to the page that has the full text. Audit snippet worth reusing:
  ```js
  [...document.querySelectorAll('*')].filter(el => /(auto|scroll)/.test(getComputedStyle(el).overflowY)
    && el.scrollHeight > el.clientHeight + 4 && el !== document.documentElement && el !== document.body)
  ```
