# The confidence field is a router, and it worked end to end

*From LEARNINGS.md, section "2026-09-04 — Opus second pass, agent-fleet operations".*

**The confidence field is a router, and it worked end to end.** Sonnet flags cheap (101 low of 702), Opus resolves expensive (100 of 101 → medium/high; 1 stayed low because ~75% of the frames are genuinely black). The same flags doubled as detectors: "4+ settings" found 8 compilation videos (audio fingerprints, limited to the first 60 s, had mapped only 2), and one agent pixel-diffed two sheets and independently rediscovered a known duplicate pair (mean diff 0.67/255).
