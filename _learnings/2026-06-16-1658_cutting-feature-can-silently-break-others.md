# Cutting a feature can silently break others

*From LEARNINGS.md, section "Website v2 — EDA, discovery, layout (2026-06-16)".*

**Cutting a feature can silently break others.** Dropping "shareable search URLs" left the watch-page tags and Stats labels with nowhere to link (the home couldn't accept a URL filter). Resolved with a *minimal* internal `?location=`/`?actor=` seed — distinct from the full shareable-URL feature. Lesson: when you cut scope, grep for who depended on it.
