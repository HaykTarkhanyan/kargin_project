# DNS for karginhaghordum.am — STEP 1B (one more TXT record)

Follow-up to `DNS_HANDOFF_karginhaghordum.md`. Status as of 2026-09-12:

- STEP 1 worked: the `hosting-site=kargin-archive` TXT record is live and
  Firebase has verified domain ownership.
- The TLS certificate is NOT ready yet, and it cannot finish in the current
  setup: Firebase's HTTP validation probe hits the old GitHub Pages IPs
  (which 404 it). One more TXT record lets Firebase validate over DNS
  instead, with zero downtime. The token below is generated per-domain by
  Firebase and was not yet known when the original doc was written.

**This is still not STEP 2. Do NOT touch the A records yet.**

---

## Do now: add ONE TXT record

In the name.am DNS zone editor for `karginhaghordum.am`, **add**:

| Type | Host / Name | Value | TTL |
|---|---|---|---|
| TXT | `_acme-challenge` | `OB12BPrIpcIC1CVxBHhvnp-AEqMmlri-EGeJnNSMYZ4` | lowest available |

- The full record name is `_acme-challenge.karginhaghordum.am` — if the
  panel wants the fully qualified name, use that; if it wants only the
  subdomain part, use `_acme-challenge` (keep the leading underscore).
- The value is the token exactly as written, nothing added around it.
- **Keep** the existing `hosting-site=kargin-archive` TXT record.
- **Do not** remove or modify the four A records — the site must keep
  serving from GitHub Pages until Hayk confirms the certificate is ready.
- Change nothing else in the zone.

**Check it worked** (may take a few minutes to appear):

```
nslookup -type=TXT _acme-challenge.karginhaghordum.am
# expect: text = "OB12BPrIpcIC1CVxBHhvnp-AEqMmlri-EGeJnNSMYZ4"
```

**Then tell Hayk.** Hayk will watch the certificate mint (minutes to a few
hours) and only then send the go-ahead for STEP 2 (the A-record swap) from
the original doc.

---

## Separate item: accept the Google Cloud invitation (not a DNS step)

Hayk has invited `mherkhachatryan35912@gmail.com` to be an **Owner** of the
Google Cloud / Firebase project behind the site (project `kargin-archive`).

- There is an invitation email from Google Cloud in that Gmail inbox
  (sent 2026-09-12). Open it and click accept — this must be done while
  signed in to Google as `mherkhachatryan35912@gmail.com`.
- Until it is accepted, the grant is inactive ("Pending acceptance") and
  gives no access. Invitations can expire, so accepting soon is better;
  if it has expired, tell Hayk and a new one will be sent.
- This is independent of the DNS work above — accepting it does not
  change anything on name.am, and the DNS steps do not depend on it.

## If anything looks off

Change nothing further and message Hayk. Same rule as before: the failure
mode to avoid is removing the old A records before the certificate exists.
