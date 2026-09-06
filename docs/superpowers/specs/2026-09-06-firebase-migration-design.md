# Design: migrate hosting to Firebase, adopt Firestore

Date: 2026-09-06
Status: reviewed — independent adversarial review 2026-09-06, all findings incorporated below

## Context

The site (`web/`) is a Next.js 16 **static export** (`output: "export"`), deployed to GitHub Pages
at `karginhaghordum.am` (DNS already configured, `web/public/CNAME`). All sketch data is baked in at
build time: `scripts/build_site_data.py` produces `web/public/data/sketches.json` (~2.6 MB, 702
sketches), which `web/lib/data.ts` **imports at build time** — the data ships inside content-hashed
JS chunks, so every data push invalidates those chunks for repeat visitors. Search is client-side
fuse.js. The only backend is `logger-worker/` — a Cloudflare Worker that inserts anonymous usage
events into Neon Postgres, because a static site cannot hold a DB credential.

## Goals

1. Host the site on Firebase (GCP) instead of GitHub Pages, keeping the custom domain.
2. Replace the Cloudflare Worker + Neon logging stack with Firestore.
3. Mirror sketch data into Firestore as the foundation for future dynamic features
   (view counters, favorites, submissions).
4. Keep `kargin_eng.csv` + annotation files in git as the **source of truth** for sketch data.

## Non-goals

- Server-side rendering. The static export stays. (Decided against Firebase App Hosting SSR:
  its only benefit — data updates without rebuild — is void because data edits are git commits,
  and every push already rebuilds via CI. Revisit only if data starts being edited outside git.)
- Serving the **search index** from Firestore. Search keeps the statically bundled JSON.
  702 Firestore doc reads per visitor would be slower and burn the free quota (50k reads/day)
  at ~70 visitors/day.
- Building any dynamic feature now. This migration only lays the foundation.
- SQL analytics over events. Follow-up: the Firestore→BigQuery export extension (needs Blaze,
  which we have). **Until then the analytics story regresses vs Neon**: events are effectively
  write-only — console spot-checks are fine, bulk reads burn the 50k/day read quota.
- Cloud Functions, Firebase Auth, App Check — none in scope.

## Decisions (made with the user 2026-09-06; revised after independent review)

- Architecture: static export on **classic Firebase Hosting** + Firestore for events and a
  sketch mirror. Alternatives rejected: App Hosting SSR (cost + big code migration for no real
  benefit), hybrid static-plus-rehydrate (two data paths for the same content).
- Source of truth stays the CSV in git; a sync script pushes to Firestore.
- **Blaze plan with a budget alert (~$10)**, not Spark. Spark's Hosting transfer cap
  (10 GB/month) *disables the site* when exceeded; the built export is ~103 MB and one viral
  link could plausibly hit the cap. Blaze keeps all free allowances and turns an outage into a
  small bill — consistent with the approved "a few $/month". Expected steady-state cost ≈ $0.
- Events transport: **Firestore REST `documents:commit` + `fetch(keepalive)`, no SDK** —
  preserves today's tab-close delivery semantics with zero SDK bytes. Alternatives rejected:
  full web SDK (large, and a lazy import at flush time loses short sessions entirely),
  `firebase/firestore/lite` (smaller but still no keepalive guarantee on unload).

## Architecture

```
git push → GitHub Actions:
  Python tests → build_site_data.py (CSV → sketches.json)
  → lint / typecheck / unit tests → next build
  → firebase deploy --only firestore:rules,hosting          [REPLACES deploy-pages]
  → sync_firestore.py (sketches.json → Firestore `sketches`) [NEW — after deploy succeeds,
                                                              so the mirror never leads the site]

Browser:
  static pages (sketch data inside JS chunks) from Firebase Hosting CDN — unchanged UX
  lib/log.ts → clamp fields → REST commit via fetch(keepalive) → Firestore `events`
```

## Firebase project

- One new Firebase project (name chosen at creation, e.g. `kargin-archive`), **Blaze** plan,
  budget alert at ~$10/month.
- A registered **web app** in the project (this produces the `NEXT_PUBLIC_FIREBASE_*` config).
- Firestore, Native mode, the **`(default)` database** (free quotas apply only to it),
  location **`europe-west3` (Frankfurt** — closest region to Armenia; location is immutable).
  Created in **production (locked) mode**; rules are deployed by CI from phase 2 on.
- Products used: Hosting, Firestore. No Functions, no Auth, no App Check (deferred).

## Data model

### `sketches/{id}` — mirror of the catalog

Doc ID = `Sketch.id` (the YouTube video id). Fields = the `Sketch` interface in
`web/lib/types.ts` verbatim (title, url, text, actors, songs, transcript, visual, …;
avg ~3.8 KB/doc, well under the 1 MiB limit) **plus `contentHash`** — SHA-256 of the sketch's
canonical JSON, used by the sync to diff cheaply. Written only by the sync script; the site
does not read it yet.

### `events/{autoId}` — anonymous usage events

Same shape the Worker logs today (`logger-worker/schema.sql`), written client-side.
**Clamping happens client-side** (mirroring `logger-worker/src/index.ts` `clamp()`, which dies
with the Worker); rules enforce the same contract as a backstop.

| field | type | client clamp / rules cap |
|---|---|---|
| `sessionId` | string | ≤ 64 chars |
| `type` | string | `search \| open \| filter \| findname \| copy` |
| `query` | string? | ≤ 500 chars |
| `mode` | string? | ≤ 32 chars |
| `filters` | map? | rules check `is map` only (nested shape too complex for rules; client bounds it) |
| `resultCount` | number? | |
| `sketchId` | string? | ≤ 64 chars |
| `source` | string? | ≤ 32 chars |
| `ua` | string? | ≤ 256 chars (client-set now; the Worker set it server-side) |
| `ts` | timestamp | server transform `REQUEST_TIME`; rules require `ts == request.time` |

## Security rules (the load-bearing piece)

```
sketches: read: true;  write: false        // only the admin sync writes
events:   create: only, with shape validation; read/update/delete: false
```

`events` create validation: `type` in the allowlist, required fields present, string caps as
above, no unexpected keys, `ts == request.time`. Deployed to production by CI
(`firebase deploy --only firestore:rules,hosting`) and tested with the Firestore emulator
(`@firebase/rules-unit-testing`) — this is an openly writable database; the rules are the
abuse surface.

A `documents:commit` batch is atomic: one rules-violating event fails the whole batch. That is
why the client clamps first — a rules rejection means a bug or an attacker, and dropping the
batch (with `console.warn`) is fine for telemetry.

Accepted residual risk: without App Check, a determined abuser can script writes that pass
shape validation. Acceptable for anonymous telemetry (worst case: junk rows, bounded by the
20k free writes/day). App Check is the documented next step if abuse appears.

## Logging transport change (`web/lib/log.ts`)

- Keep: queue + 2 s batching, `visibilitychange` flush, silent no-op when unconfigured,
  "logging must never break the app" (all errors caught and `console.warn`ed).
- Change: flush POSTs the batch (≤ 50 events → ≤ 50 writes) to
  `https://firestore.googleapis.com/v1/projects/<pid>/databases/(default)/documents:commit`
  with `fetch(..., { keepalive: true })`. Each write carries the clamped fields plus an
  `updateTransforms` / server-value `REQUEST_TIME` for `ts`. No auth header — anonymous
  create is what the rules permit. (Keepalive bodies cap at 64 KB — with clamped fields a
  50-event batch stays well under.)
- `sendBeacon` is dropped: it can't send `application/json` without preflight complications,
  and `fetch(keepalive)` is its modern replacement with the same unload semantics — which the
  current code already uses as its fallback (`log.ts:47`).
- Config: `NEXT_PUBLIC_FIREBASE_PROJECT_ID` baked at build (public by design — security lives
  in the rules). Unset → no-op, same contract as `LOG_ENDPOINT` today.

## Sync script (`scripts/sync_firestore.py`)

- Input: `web/public/data/sketches.json` (the artifact `build_site_data.py` already produces —
  one derivation path, no re-deriving from CSV).
- Auth: service account via `GOOGLE_APPLICATION_CREDENTIALS`; in CI, a GitHub secret.
- Diff by `contentHash`: read existing id→hash pairs, write only new/changed docs, delete docs
  whose id no longer exists in the JSON. Second run with unchanged data = **0 writes**
  (this is the idempotency exit criterion). Batched ≤ 500 ops/batch.
- **Delete guard**: refuse to run if the delete set exceeds 5% of existing docs, unless an
  explicit `--allow-mass-delete` flag is passed — a valid-but-truncated JSON must not silently
  wipe the mirror.
- Fails loudly on any error (no partial-success exit 0). Runs in CI after a successful deploy;
  also runnable locally.

## CI changes (`.github/workflows/deploy.yml`)

- Replace `upload-pages-artifact`/`deploy-pages` with a Firebase deploy
  (`FirebaseExtended/action-hosting-deploy` or `firebase deploy --only firestore:rules,hosting`)
  using a service-account JSON secret (`FIREBASE_SERVICE_ACCOUNT`). Workload Identity
  Federation is the keyless upgrade path, not required now.
- Add the sync step **after** the deploy succeeds.
- New repo vars: `NEXT_PUBLIC_FIREBASE_PROJECT_ID` (replacing `LOG_ENDPOINT`).
- `firebase.json`: `trailingSlash: true` + `cleanUrls: false` (matches the export layout;
  mismatch causes redirect loops), long-cache headers for `/_next/static/**`.
- **Release storage limit**: keep last ~10 versions (console setting, phase 1). Each deploy
  stores a ~103 MB version and this repo deploys on every push; without retention the 10 GB
  Hosting storage quota fills in ~100 deploys.
- `web/public/CNAME` and `web/public/.nojekyll` are GitHub-Pages-specific → deleted at
  cutover (phase 4); harmless on Firebase until then.

## Rollout phases (each independently shippable, site never down)

1. **Hosting in parallel.** Create the Firebase project; add `firebase.json`; set release
   retention; add `metadataBase` + `rel=canonical` → `https://karginhaghordum.am` in
   `web/app/layout.tsx` (the parallel `<project>.web.app` host is duplicate content otherwise);
   deploy `web/out` to Firebase Hosting from CI alongside the Pages deploy.
   Exit: site fully works on `<project>.web.app`, canonical tag present, Pages untouched.
2. **Firestore foundation.** Rules + emulator tests; rules deploy in CI; `sync_firestore.py`;
   CI sync step after deploy. Exit: 702 docs in `sketches`, re-run sync = 0 writes,
   rules tests green, production rules verified (a manual out-of-contract write is denied).
3. **Logging switch.** New `log.ts` transport + client clamps; deploy; verify events land in
   Firestore from the live site. **Soak ≥ 3 days** so stale tabs still beaconing to the Worker
   drain out. Then, in order: export all Neon rows to `data/` as CSV backup (**export last,
   immediately before deletion** — no lost tail), delete the Worker deployment, delete the
   Neon project, move `logger-worker/` → `old/logger-worker/` with a decommission note.
4. **Cutover.** Use Firebase Hosting custom-domain **Advanced Setup** — it provisions the
   `karginhaghordum.am` cert *before* traffic moves, so there is no HTTPS-error window. Flip
   the A/AAAA records at the registrar only after the cert is issued. **Keep the Pages site
   serving until the old records' TTL has comfortably passed (days, not minutes)**, then
   remove the Pages workflow steps, the Pages site, `CNAME`, and `.nojekyll`.

## Manual steps (require the user)

- Create the Firebase project; **register a web app** in it (produces the config values);
  create the Firestore `(default)` DB in `europe-west3`, production mode.
- Upgrade to Blaze and set a ~$10 budget alert.
- Create the deploy service account key; add GitHub secret + repo vars.
- Set the Hosting release storage limit (console).
- Phase 3: Neon export credentials; approve Worker + Neon deletion.
- Phase 4: approve and perform the DNS record change at the registrar.

## Testing

- Unit: new `log.ts` transport with mocked `fetch` — clamping, batching, REST body shape,
  no-op when unconfigured, errors swallowed with a warn (existing vitest setup).
- Rules: emulator suite — valid anonymous create passes; oversized / wrong-type / extra-field /
  read / update / delete all denied; `sketches` client writes denied.
- Sync: idempotency (second run = 0 writes), delete guard triggers on a truncated input.
- Per-phase manual verification as listed in each phase's exit criteria.

## Risks

- **Traffic spike cost** (was: site-goes-dark on Spark): Blaze + budget alert converts the
  outage into a small bill; Hosting bandwidth is $0.15–0.20/GiB past 10 GiB/month.
- **Open-write abuse**: bounded; App Check is the response if it appears.
- **DNS/cert cutover**: Advanced Setup + TTL-respecting decommission delay.
- **Sync deletes**: 5% guard + fail-loud + data reproducible from any git commit.
- **Lost end-of-session events**: `fetch(keepalive)` preserves today's semantics; no regression
  expected vs the Worker path.
