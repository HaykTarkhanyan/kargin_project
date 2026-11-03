# name.am mechanics

*From LEARNINGS.md, section "2026-09-08 — custom-domain plumbing".*

**name.am mechanics**: new domains sit on `park1/2.name.am` (parking site = the A/AAAA Firebase flags for removal); the panel's "DNS Records" mode switches NS to `a-d.ns.name.am` backed by Route 53 — propagation in seconds, zone starts empty so parking records vanish with the switch. NS mode and DNS mode are exclusive; switching shows a your-site-may-go-down warning modal.
