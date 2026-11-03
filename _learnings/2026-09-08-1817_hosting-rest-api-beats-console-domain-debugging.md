# The Hosting REST API beats the console for domain debugging

*From LEARNINGS.md, section "2026-09-08 — custom-domain plumbing".*

**The Hosting REST API beats the console for domain debugging.** `firebasehosting.googleapis.com/v1beta1/projects/<id>/sites/<id>/customDomains` (explicit project id — the `projects/-` wildcard 404s) returns ownershipState/hostState/cert.state, the exact records Google's probes currently DISCOVER vs DESIRE, and even the `_acme-challenge` TXT token for a manual DNS-01 fast path. The console only says "records not yet detected".
