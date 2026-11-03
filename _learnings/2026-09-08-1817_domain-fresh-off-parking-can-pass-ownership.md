# A domain fresh off parking can pass ownership but stall the cert for hours

*From LEARNINGS.md, section "2026-09-08 — custom-domain plumbing".*

**A domain fresh off parking can pass ownership but stall the cert for hours**: Google's resolvers saw our new TXT quickly, yet kept serving the CACHED parking A/AAAA — so the cert's HTTP ACME probe kept hitting the parking webserver. Nothing was wrong; it self-healed when the parking records' TTL expired. Check `requiredDnsUpdates.discovered` before touching anything.
