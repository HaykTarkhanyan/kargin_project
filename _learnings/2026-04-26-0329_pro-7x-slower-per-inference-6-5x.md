# Pro is ~7x slower per inference and ~6.5x more expensive than Lite, but qualitatively more accurate on Armenian

*From LEARNINGS.md, section "Gemini STT spike (2026-04-26)".*

**Pro is ~7x slower per inference and ~6.5x more expensive than Lite, but qualitatively more accurate on Armenian.** Specific kinds of fixes Pro made vs Lite on hand-checked sketches: (1) recovers correct opening lines where Lite produced gibberish (`Petros, all day shake your daddies` → `Petrosyan, you're preparing yesterday's contract papers`), (2) uses world knowledge to disambiguate names/places (`Naas darks, Dou Jones` → `Nasdaq, Dow Jones`), (3) gets the right verb register and grammar even when the dialogue is colloquial. The latency cost is "thinking budget" being spent on disambiguation — causally linked to the quality lift, not coincidental.
