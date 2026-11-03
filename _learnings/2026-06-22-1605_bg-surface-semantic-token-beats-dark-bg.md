# `bg-surface` semantic token beats the `.dark .bg-white{...}` descendant override

*From LEARNINGS.md, section "From the codebase-review cleanup (2026-06-22)".*

**`bg-surface` semantic token beats the `.dark .bg-white{...}` descendant override.** The earlier dark-theme pass re-themed white surfaces with an unlayered `.dark .bg-white` rule. It's brittle: it silently misses `text-white`, every new `bg-white` author must know the global exists, and in dark mode it forced one fixed `#1f1f27` regardless of context. Cleaner: define a `--surface` token (`@theme inline` → `--color-surface`) that flips in `.dark`, and use `bg-surface`. Same pixels (light `#FFFFFF`, dark `#1f1f27`), no magic selector. Reserve a distinct token value from `card`/`paper2` if you want "raised" surfaces to stand off the panel in dark mode (card and paper2 are near-identical there).
