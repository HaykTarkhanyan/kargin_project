# Precompute EDA in Python, render with hand-rolled SVG/CSS

*From LEARNINGS.md, section "Website v2 — EDA, discovery, layout (2026-06-16)".*

**Precompute EDA in Python, render with hand-rolled SVG/CSS.** `stats.json` (aggregates, co-occurrence matrix, bigrams) keeps tokenization server-side and the client lean; SVG/CSS charts (scatter, heatmap, trend, treemap) match the brutalist look and avoid a charting dependency entirely. Bigrams (`ցավդ տանեմ`, `ախпер ջан`) are far more interesting than single-word frequency (which is mostly function words).
