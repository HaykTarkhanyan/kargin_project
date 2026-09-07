# DNS changes for karginhaghordum.am — instructions for Mher (or his coding agent)

Hayk is moving the website `karginhaghordum.am` from GitHub Pages to Firebase
Hosting (Google Cloud). The domain's DNS is managed in **Mher's name.am
account** (nameservers `a/b/c.ns.name.am`), so two small DNS edits are needed
there. Done in this order there is **zero downtime**: the old site keeps
serving until the new one has its TLS certificate ready.

**The two steps are gated. Do STEP 1 now. Do NOT do STEP 2 until Hayk
explicitly confirms the certificate is ready.**

---

## Current state (for reference — verified 2026-09-07)

| Type | Host | Value | Meaning |
|---|---|---|---|
| A | `karginhaghordum.am` (apex) | 185.199.108.153 | GitHub Pages |
| A | `karginhaghordum.am` (apex) | 185.199.109.153 | GitHub Pages |
| A | `karginhaghordum.am` (apex) | 185.199.110.153 | GitHub Pages |
| A | `karginhaghordum.am` (apex) | 185.199.111.153 | GitHub Pages |

---

## STEP 1 — do now: add ONE TXT record (nothing else changes)

In the name.am DNS zone editor for `karginhaghordum.am`, **add**:

| Type | Host / Name | Value | TTL |
|---|---|---|---|
| TXT | apex — `@`, blank, or `karginhaghordum.am` depending on the panel | `hosting-site=kargin-archive` | lowest available (300–600 s if offered) |

- Do **not** remove or modify the four A records yet — the site must keep
  serving from GitHub Pages during this step.
- If the panel offers a TTL setting on the A records, lowering them to 300–600 s
  now is helpful (makes the final switch propagate faster) but optional.

**Check it worked** (may take a few minutes to appear):

```
nslookup -type=TXT karginhaghordum.am
# expect: text = "hosting-site=kargin-archive"
```

**Then tell Hayk step 1 is done.** Firebase will verify domain ownership via
that TXT record and mint the TLS certificate for the domain. This can take
minutes to a few hours. The old site keeps running the whole time.

---

## STEP 2 — ONLY after Hayk says "certificate ready": swap the A records

**Remove** the four GitHub Pages A records:

| Type | Host | Value — REMOVE |
|---|---|---|
| A | apex | 185.199.108.153 |
| A | apex | 185.199.109.153 |
| A | apex | 185.199.110.153 |
| A | apex | 185.199.111.153 |

**Add** the single Firebase A record:

| Type | Host / Name | Value — ADD | TTL |
|---|---|---|---|
| A | apex | `199.36.158.100` | 300–600 s if offered |

Also, while in the zone editor, **check and report** (do not silently change):

- Any **AAAA** (IPv6) records on the apex — GitHub Pages setups sometimes have
  `2606:50c0:8000::153`–`2606:50c0:8003::153`. If present they MUST be removed
  in this step too, otherwise IPv6 visitors keep hitting the old host.
- Any **`www`** subdomain record (CNAME to `hayktarkhanyan.github.io` or
  similar). If it exists, report it to Hayk — it will be repointed separately.
- **Keep** the TXT record from step 1 (Firebase re-checks it periodically).
- **Do not** change nameservers, MX, or anything else in the zone.

**Check it worked:**

```
nslookup -type=A karginhaghordum.am
# expect exactly one address: 199.36.158.100
```

Then `https://karginhaghordum.am` serves the new site with a valid certificate
(allow up to the old records' TTL for stragglers). Done — tell Hayk.

---

## If anything looks off

Change nothing further and message Hayk. The worst failure mode here is
removing the old A records before the certificate exists (visitors would get
HTTPS errors) — which is exactly what the two-step gating prevents.
