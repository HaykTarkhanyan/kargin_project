# Dark theme on a token-based design is cheap; the leaks are the hardcoded colors

*From LEARNINGS.md, section "Website v2 — EDA, discovery, layout (2026-06-16)".*

**Dark theme on a token-based design is cheap; the leaks are the hardcoded colors.** Flipping the CSS variables in a `.dark` class re-themes everything that uses the tokens (`bg-paper`, `text-ink`, `.k-shadow` → light offset shadow on dark, motif preserved) — for free. The work is the *non-token* colors: `bg-white` surfaces (override once: `.dark .bg-white{...}`, which wins as unlayered CSS over Tailwind's layered utility), SVG presentation attrs hardcoded to ink (`stroke="#1A1410"` → `className="stroke-ink"` so they flip), and inline pastel cells (pin an explicit dark text color so they're readable in both themes). A pre-paint inline `<script>` reading localStorage avoids the flash; `suppressHydrationWarning` on `<html>` silences the class mismatch.
