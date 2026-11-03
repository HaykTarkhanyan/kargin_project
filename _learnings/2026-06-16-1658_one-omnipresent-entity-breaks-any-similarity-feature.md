# One omnipresent entity breaks any "similarity" feature

*From LEARNINGS.md, section "Website v2 — EDA, discovery, layout (2026-06-16)".*

**One omnipresent entity breaks any "similarity" feature.** Հայko/Мко are in ~76% of sketches, so "related by shared actor" returns nearly the whole corpus → degenerates to "globally most-viewed on every page." Fix = **rarity-weighting**: score a shared actor by `1/frequency`, so a shared *guest* (Հасмик/Аshот) outweighs the ubiquitous duo. Same failure shape as the `Այլ` location catch-all (52% of rows) — exclude or down-weight the dominant value.
