# Firebase Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move hosting from GitHub Pages to Firebase Hosting and replace the Cloudflare Worker + Neon logging with a rules-guarded Firestore `events` collection, plus a CI-synced `sketches` mirror.

**Architecture:** The Next.js static export stays untouched; `web/` gains Firebase config (`firebase.json`, rules, emulator tests), `scripts/` gains a hash-diffing Firestore sync, and `web/lib/log.ts` swaps its transport to Firestore's REST `documents:commit` via `fetch(keepalive)`. Four phases, each shippable, site never down. Spec: `docs/superpowers/specs/2026-09-06-firebase-migration-design.md`.

**Tech Stack:** firebase-tools (dev dep), Firestore emulator (needs Java 21 — portable JRE in `~/.jdks`), `@firebase/rules-unit-testing` + vitest, `google-cloud-firestore` (Python, new `firebase` dep group), GitHub Actions.

**Status 2026-09-06:** Tasks 1, 2, 3, 5, 6, 7, 8 complete and committed (all local verifications
green). Task 9's soak/export steps are void — the Worker+Neon stack was never activated
(`LOG_ENDPOINT` never set), so `logger-worker/` was archived to `old/` directly. Remaining:
Task 4 (user: create project, Blaze, secrets/vars), Task 9 live-event verification,
Task 10 (user: DNS cutover, retire Pages).

**Conventions that bind every task:** exact version pins (`==` / exact npm versions — pin whatever `npm i` / `uv add` actually installed), Python `logging` to console + `logs/<script>.log`, no silent fallbacks — fail loudly.

---

## Phase 1 — Hosting in parallel

### Task 1: firebase-tools + `firebase.json` + local hosting smoke test

**Files:**
- Create: `web/firebase.json`, `web/.firebaserc`
- Modify: `web/package.json` (dev dep)

- [ ] **Step 1: Install firebase-tools as a dev dependency** (pins the version in package-lock; CI and local use the same binary)

Run in `web/`: `npm i -D firebase-tools`
Then set the exact installed version (no `^`) in `package.json` devDependencies.

- [ ] **Step 2: Create `web/firebase.json`** (hosting only — the firestore block arrives in Task 5)

```json
{
  "hosting": {
    "public": "out",
    "cleanUrls": false,
    "trailingSlash": true,
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "headers": [
      {
        "source": "/_next/static/**",
        "headers": [
          { "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }
        ]
      }
    ]
  },
  "emulators": {
    "hosting": { "port": 5005 },
    "firestore": { "port": 8080 },
    "ui": { "enabled": false }
  }
}
```

`cleanUrls: false` + `trailingSlash: true` matches the export layout (`next.config.ts` has `trailingSlash: true`); a mismatch causes redirect loops.

- [ ] **Step 3: Create `web/.firebaserc`** (placeholder id; Task 4 fixes it if the real project id differs)

```json
{
  "projects": { "default": "kargin-archive" }
}
```

- [ ] **Step 4: Build and smoke-test through the hosting emulator**

Run in `web/`:
```bash
npm run build
npx firebase emulators:start --only hosting --project demo-kargin &
sleep 8
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5005/            # expect 200
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5005/about/      # expect 200
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5005/nope/       # expect 404
```
Kill the emulator afterwards. (`demo-` prefix = emulator-only project, no credentials.)

- [ ] **Step 5: Commit**

```bash
git add web/firebase.json web/.firebaserc web/package.json web/package-lock.json
git commit -m "feat(web): Firebase Hosting config + firebase-tools dev dep"
```

### Task 2: canonical URL (the parallel `*.web.app` host must not become duplicate content)

**Files:**
- Modify: `web/app/layout.tsx:10-13`

- [ ] **Step 1: Add `metadataBase` + per-page canonical**

```tsx
export const metadata: Metadata = {
  metadataBase: new URL("https://karginhaghordum.am"),
  alternates: { canonical: "./" },
  title: "Կարգին Արխիվ — Kargin Archive",
  description: "Որոնիր 702 Կարգին սքեթչ՝ տող առ տող։",
};
```

`"./"` resolves per route, so every page canonicalizes to its own `karginhaghordum.am` URL. First consult the Next 16 metadata doc in `web/node_modules/next/dist/docs/` (per `web/AGENTS.md`) to confirm the field names are unchanged.

- [ ] **Step 2: Verify in the build output**

Run in `web/`: `npm run build`, then check both a root and a nested page:
```bash
grep -o '<link rel="canonical"[^>]*>' out/index.html          # expect href="https://karginhaghordum.am/"
grep -o '<link rel="canonical"[^>]*>' out/about/index.html    # expect href=".../about/"
```

- [ ] **Step 3: Run the existing test suite** — `npm test`, `npx tsc --noEmit`, `npm run lint` in `web/`. Expect all green.

- [ ] **Step 4: Commit**

```bash
git add web/app/layout.tsx
git commit -m "feat(web): canonical URLs pointing at karginhaghordum.am"
```

### Task 3: CI — deploy to Firebase Hosting alongside Pages

**Files:**
- Modify: `.github/workflows/deploy.yml` (build job, after the `npm run build` step)

- [ ] **Step 1: Add the Firebase deploy step** (gated on the repo var so the workflow stays green until Task 4 sets it)

```yaml
      - name: Deploy to Firebase Hosting
        if: ${{ vars.FIREBASE_PROJECT_ID != '' }}
        working-directory: web
        env:
          FIREBASE_SA: ${{ secrets.FIREBASE_SERVICE_ACCOUNT }}
        run: |
          printf '%s' "$FIREBASE_SA" > "$RUNNER_TEMP/firebase-sa.json"
          export GOOGLE_APPLICATION_CREDENTIALS="$RUNNER_TEMP/firebase-sa.json"
          npx firebase deploy --only hosting --project "${{ vars.FIREBASE_PROJECT_ID }}" --force
```

The Pages `upload-pages-artifact` / `deploy` job stays untouched — both hosts run in parallel until phase 4.

- [ ] **Step 2: Commit** (deploy fires on push; until Task 4 the new step is skipped)

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: parallel deploy to Firebase Hosting (no-op until FIREBASE_PROJECT_ID is set)"
```

### Task 4: USER ACTION — create the Firebase project

Everything here happens in the Firebase/GCP console (or `npx firebase login` + CLI). Checklist for the user:

- [ ] Create the Firebase project (suggested id: `kargin-archive`; if different, update `web/.firebaserc`).
- [ ] **Register a web app** in the project (Project settings → Your apps) — we only need the project to accept web traffic; the config values beyond the project id are not used by this design.
- [ ] Create the Firestore **`(default)`** database: Native mode, location **`europe-west3`**, **production (locked) mode**.
- [ ] Upgrade to **Blaze**, set a budget alert (~$10/month) in Google Cloud Billing.
- [ ] Hosting → release storage: set retention to keep the last ~10 versions.
- [ ] Create a service account key: GCP Console → IAM → Service accounts → `firebase-adminsdk-…` (or a new SA with roles `Firebase Hosting Admin`, `Cloud Datastore User`, `Firebase Rules Admin`) → JSON key.
- [ ] GitHub repo → Settings → Secrets and variables → Actions:
  - Secret `FIREBASE_SERVICE_ACCOUNT` = the JSON key contents
  - Variable `FIREBASE_PROJECT_ID` = the project id
- [ ] Push / re-run the workflow. **Phase 1 exit:** site fully browsable at `https://<project-id>.web.app`, canonical tags present, GitHub Pages untouched.

---

## Phase 2 — Firestore foundation

### Task 5: security rules, TDD against the emulator

**Files:**
- Create: `web/firestore.rules`, `web/firestore.indexes.json`, `web/rules-tests/rules.test.ts`, `web/vitest.rules.config.ts`
- Modify: `web/firebase.json` (firestore block), `web/vitest.config.ts` (exclude rules-tests), `web/package.json` (deps + script)

- [ ] **Step 1: Install rules test deps** in `web/`: `npm i -D firebase @firebase/rules-unit-testing` (pin exact versions in package.json; `firebase` is a peer dep of the test lib — dev-only, never bundled).

- [ ] **Step 2: Write the failing rules tests** — `web/rules-tests/rules.test.ts`:

```ts
import { readFileSync } from "node:fs";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import {
  assertFails,
  assertSucceeds,
  initializeTestEnvironment,
  type RulesTestEnvironment,
} from "@firebase/rules-unit-testing";
import { collection, deleteDoc, doc, getDoc, getDocs, serverTimestamp, setDoc, updateDoc } from "firebase/firestore";

let env: RulesTestEnvironment;

beforeAll(async () => {
  const [host, port] = (process.env.FIRESTORE_EMULATOR_HOST ?? "127.0.0.1:8080").split(":");
  env = await initializeTestEnvironment({
    projectId: "demo-kargin",
    firestore: { host, port: Number(port), rules: readFileSync("firestore.rules", "utf8") },
  });
});
afterAll(async () => { await env.cleanup(); });

const anon = () => env.unauthenticatedContext().firestore();
const valid = () => ({ sessionId: "s1", type: "search", query: "բարեւ", resultCount: 3, source: "home", ua: "test", ts: serverTimestamp() });

describe("events", () => {
  it("accepts a valid anonymous create", async () => {
    await assertSucceeds(setDoc(doc(anon(), "events", "e1"), valid()));
  });
  it("rejects an unknown type", async () => {
    await assertFails(setDoc(doc(anon(), "events", "e2"), { ...valid(), type: "hack" }));
  });
  it("rejects an oversized query", async () => {
    await assertFails(setDoc(doc(anon(), "events", "e3"), { ...valid(), query: "x".repeat(501) }));
  });
  it("rejects unexpected keys", async () => {
    await assertFails(setDoc(doc(anon(), "events", "e4"), { ...valid(), admin: true }));
  });
  it("rejects a client-chosen timestamp", async () => {
    await assertFails(setDoc(doc(anon(), "events", "e5"), { ...valid(), ts: new Date() }));
  });
  it("rejects a non-string filters value", async () => {
    await assertFails(setDoc(doc(anon(), "events", "e6"), { ...valid(), filters: { loc: ["a"] } }));
  });
  it("denies read, update, delete", async () => {
    await env.withSecurityRulesDisabled(async (ctx) =>
      setDoc(doc(ctx.firestore(), "events", "seed"), { sessionId: "s", type: "open" }));
    await assertFails(getDocs(collection(anon(), "events")));
    await assertFails(updateDoc(doc(anon(), "events", "seed"), { type: "copy" }));
    await assertFails(deleteDoc(doc(anon(), "events", "seed")));
  });
});

describe("sketches", () => {
  it("allows public read, denies client write", async () => {
    await env.withSecurityRulesDisabled(async (ctx) =>
      setDoc(doc(ctx.firestore(), "sketches", "abc"), { title: "t" }));
    await assertSucceeds(getDoc(doc(anon(), "sketches", "abc")));
    await assertFails(setDoc(doc(anon(), "sketches", "zzz"), { title: "nope" }));
  });
});
```

- [ ] **Step 3: Wire the runner.** `web/vitest.rules.config.ts`:

```ts
import { defineConfig } from "vitest/config";
export default defineConfig({
  test: { include: ["rules-tests/**/*.test.ts"], environment: "node", testTimeout: 20000 },
});
```

In `web/vitest.config.ts` add `"rules-tests/**"` to the test `exclude` list (read the file first; extend, don't replace).
In `web/package.json` scripts:
```json
"test:rules": "firebase emulators:exec --only firestore --project demo-kargin \"vitest run --config vitest.rules.config.ts\""
```
Add to `web/firebase.json` (top level):
```json
"firestore": { "rules": "firestore.rules", "indexes": "firestore.indexes.json" }
```
And create `web/firestore.indexes.json`:
```json
{ "indexes": [], "fieldOverrides": [] }
```

- [ ] **Step 4: Run with an empty-deny rules file to see the suite fail** — create `web/firestore.rules` with only:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
  }
}
```

Run in `web/`: `npm run test:rules`. Expected: the "accepts a valid anonymous create" and "allows public read" tests FAIL (everything denied), the deny tests pass.

- [ ] **Step 5: Write the real rules** — `web/firestore.rules`:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    function isValidEvent() {
      let d = request.resource.data;
      return d.keys().hasOnly(['sessionId', 'type', 'query', 'mode', 'filters',
                               'resultCount', 'sketchId', 'source', 'ua', 'ts'])
        && d.sessionId is string && d.sessionId.size() <= 64
        && d.type in ['search', 'open', 'filter', 'findname', 'copy']
        && d.ts == request.time
        && (!('query' in d)       || (d.query is string && d.query.size() <= 500))
        && (!('mode' in d)        || (d.mode is string && d.mode.size() <= 32))
        && (!('filters' in d)     || (d.filters is string && d.filters.size() <= 1000))
        && (!('resultCount' in d) || d.resultCount is int)
        && (!('sketchId' in d)    || (d.sketchId is string && d.sketchId.size() <= 64))
        && (!('source' in d)      || (d.source is string && d.source.size() <= 32))
        && (!('ua' in d)          || (d.ua is string && d.ua.size() <= 256));
    }

    match /sketches/{id} {
      allow read: if true;
      allow write: if false;   // only the admin sync writes
    }

    match /events/{id} {
      allow create: if isValidEvent();
      allow read, update, delete: if false;
    }
  }
}
```

- [ ] **Step 6: Run `npm run test:rules` — expect all PASS.**

- [ ] **Step 7: Commit**

```bash
git add web/firestore.rules web/firestore.indexes.json web/rules-tests/ web/vitest.rules.config.ts web/vitest.config.ts web/firebase.json web/package.json web/package-lock.json
git commit -m "feat(web): Firestore security rules + emulator test suite"
```

### Task 6: `scripts/sync_firestore.py`, TDD on the pure logic

**Files:**
- Create: `scripts/sync_firestore.py`, `tests/test_sync_firestore.py`
- Modify: `pyproject.toml` (new `firebase` dep group)

- [ ] **Step 1: Add the dependency**: `uv add --group firebase google-cloud-firestore`, then change the constraint in `pyproject.toml` to `==` the version `uv pip list` shows, with the group comment style matching the existing groups.

- [ ] **Step 2: Write failing tests** — `tests/test_sync_firestore.py` (pure logic only; no network, no emulator):

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import pytest
from sync_firestore import content_hash, plan_sync, check_delete_guard

def test_content_hash_is_stable_and_key_order_independent():
    a = {"id": "x", "title": "t", "actors": ["a", "b"]}
    b = {"actors": ["a", "b"], "title": "t", "id": "x"}
    assert content_hash(a) == content_hash(b)
    assert content_hash(a) != content_hash({**a, "title": "changed"})

def test_content_hash_survives_armenian_text():
    assert len(content_hash({"text": "Կարգին"})) == 64

def test_plan_sync_diffs_by_hash():
    desired = {"a": "h1", "b": "h2", "c": "h3"}
    existing = {"a": "h1", "b": "OLD", "d": "h4"}
    to_write, to_delete = plan_sync(desired, existing)
    assert to_write == ["b", "c"]      # changed + new, sorted
    assert to_delete == ["d"]          # gone from desired

def test_plan_sync_second_run_is_empty():
    desired = {"a": "h1"}
    assert plan_sync(desired, dict(desired)) == ([], [])

def test_delete_guard_blocks_mass_delete():
    with pytest.raises(RuntimeError, match="mass delete"):
        check_delete_guard(existing_count=700, delete_count=100, allow=False)

def test_delete_guard_allows_small_or_forced():
    check_delete_guard(existing_count=700, delete_count=10, allow=False)   # < 5%
    check_delete_guard(existing_count=700, delete_count=100, allow=True)   # forced
    check_delete_guard(existing_count=0, delete_count=0, allow=False)      # empty mirror
```

Run: `PYTHONPATH=scripts uv run pytest tests/test_sync_firestore.py -q` → expect FAIL (module missing).

- [ ] **Step 3: Implement `scripts/sync_firestore.py`**:

```python
"""Mirror web/public/data/sketches.json into the Firestore `sketches` collection.

Diffs by a contentHash field so an unchanged corpus produces zero writes.
Deletes docs that left the JSON, but refuses to delete >5% of the mirror
unless --allow-mass-delete is passed (a truncated-but-valid JSON must not
silently wipe it). Fails loudly on any error. Runs in CI after a successful
deploy; also runnable locally with GOOGLE_APPLICATION_CREDENTIALS set.
"""
import argparse
import hashlib
import json
import logging
import os
import sys
from pathlib import Path

SKETCHES_JSON = Path("web/public/data/sketches.json")
DELETE_GUARD_FRACTION = 0.05
BATCH_LIMIT = 400  # Firestore caps batches at 500 ops; stay clear of it

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("logs/sync_firestore.log", encoding="utf-8")],
)
log = logging.getLogger("sync_firestore")


def content_hash(sketch: dict) -> str:
    canonical = json.dumps(sketch, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def plan_sync(desired: dict[str, str], existing: dict[str, str]) -> tuple[list[str], list[str]]:
    """desired/existing map sketch id -> contentHash. Returns (to_write, to_delete), sorted."""
    to_write = sorted(i for i, h in desired.items() if existing.get(i) != h)
    to_delete = sorted(set(existing) - set(desired))
    return to_write, to_delete


def check_delete_guard(existing_count: int, delete_count: int, allow: bool) -> None:
    if allow or delete_count == 0:
        return
    if delete_count > existing_count * DELETE_GUARD_FRACTION:
        raise RuntimeError(
            f"mass delete blocked: {delete_count} of {existing_count} mirror docs would be "
            f"deleted (> {DELETE_GUARD_FRACTION:.0%}). Re-run with --allow-mass-delete if intended."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=os.environ.get("FIREBASE_PROJECT_ID"), help="GCP project id")
    parser.add_argument("--dry-run", action="store_true", help="plan only, write nothing")
    parser.add_argument("--allow-mass-delete", action="store_true")
    args = parser.parse_args()
    if not args.project:
        parser.error("--project or FIREBASE_PROJECT_ID required")

    sketches = json.loads(SKETCHES_JSON.read_text(encoding="utf-8"))
    if not isinstance(sketches, list) or not sketches:
        raise RuntimeError(f"{SKETCHES_JSON} is empty or not a list — refusing to sync")
    by_id = {s["id"]: s for s in sketches}
    if len(by_id) != len(sketches):
        raise RuntimeError("duplicate sketch ids in sketches.json")
    desired = {i: content_hash(s) for i, s in by_id.items()}

    from google.cloud import firestore  # deferred: pure-logic tests need no credentials

    db = firestore.Client(project=args.project)
    col = db.collection("sketches")
    # to_dict().get, not snap.get(): snap.get raises KeyError on docs missing the field
    existing = {snap.id: (snap.to_dict().get("contentHash") or "") for snap in col.select(["contentHash"]).stream()}

    to_write, to_delete = plan_sync(desired, existing)
    check_delete_guard(len(existing), len(to_delete), args.allow_mass_delete)
    log.info(f"mirror: {len(existing)} existing, {len(desired)} desired -> "
             f"{len(to_write)} writes, {len(to_delete)} deletes{' (dry-run)' if args.dry_run else ''}")
    if args.dry_run:
        return

    ops = 0
    batch = db.batch()
    for sid in to_write:
        batch.set(col.document(sid), {**by_id[sid], "contentHash": desired[sid]})
        ops += 1
        if ops % BATCH_LIMIT == 0:
            batch.commit(); batch = db.batch()
    for sid in to_delete:
        batch.delete(col.document(sid))
        ops += 1
        if ops % BATCH_LIMIT == 0:
            batch.commit(); batch = db.batch()
    if ops % BATCH_LIMIT:
        batch.commit()
    log.info(f"done: {len(to_write)} written, {len(to_delete)} deleted")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("sync failed")
        sys.exit(1)
```

- [ ] **Step 4: Run the tests — expect PASS**: `PYTHONPATH=scripts uv run pytest tests/test_sync_firestore.py -q`. Also run the full suite (`PYTHONPATH=. uv run pytest -q`) to confirm nothing else broke.

- [ ] **Step 5: Emulator end-to-end check** (no credentials needed): in one shell `cd web && npx firebase emulators:start --only firestore --project demo-kargin`; in another:

```bash
FIRESTORE_EMULATOR_HOST=127.0.0.1:8080 uv run --group firebase python scripts/sync_firestore.py --project demo-kargin
FIRESTORE_EMULATOR_HOST=127.0.0.1:8080 uv run --group firebase python scripts/sync_firestore.py --project demo-kargin
```
Expected: first run logs `702 writes, 0 deletes`; second run logs `0 writes, 0 deletes` (the idempotency exit criterion).

- [ ] **Step 6: Commit**

```bash
git add scripts/sync_firestore.py tests/test_sync_firestore.py pyproject.toml uv.lock
git commit -m "feat(scripts): hash-diffing Firestore sketch mirror sync with delete guard"
```

### Task 7: CI — deploy rules, then sync after a successful deploy

**Files:**
- Modify: `.github/workflows/deploy.yml`

- [ ] **Step 1: Extend the Task 3 deploy step** from `--only hosting` to `--only firestore,hosting`, and add the sync step immediately after it:

```yaml
      - name: Sync sketches to Firestore
        if: ${{ vars.FIREBASE_PROJECT_ID != '' }}
        env:
          GOOGLE_APPLICATION_CREDENTIALS: ${{ runner.temp }}/firebase-sa.json
        run: uv run --group firebase python scripts/sync_firestore.py --project "${{ vars.FIREBASE_PROJECT_ID }}"
```

The ordering is the invariant from the design review: the mirror must never lead the deployed site, so sync runs only after `firebase deploy` succeeded. (`uv sync --group review` at the top of the job must become `uv sync --group review --group firebase`.)

- [ ] **Step 2: Commit and push; watch the run.** **Phase 2 exit:** CI green; Firestore console shows 702 `sketches` docs; a second CI run logs `0 writes`; a manual out-of-contract write from the browser console is denied (verifies production rules, not just emulator).

---

## Phase 3 — Logging switch

### Task 8: rewrite `web/lib/log.ts` to the REST transport, TDD

**Files:**
- Create: `web/lib/__tests__/log.test.ts`
- Modify: `web/lib/log.ts`, `.github/workflows/deploy.yml` (build env var)

- [ ] **Step 1: Write the failing tests** — `web/lib/__tests__/log.test.ts`:

```ts
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const PROJECT = "kargin-test";
const url = (calls: ReturnType<typeof vi.fn>["mock"]["calls"]) => calls[0][0] as string;
const body = (calls: ReturnType<typeof vi.fn>["mock"]["calls"]) => JSON.parse(calls[0][1].body as string);

let fetchMock: ReturnType<typeof vi.fn>;

async function freshLog(projectId: string) {
  vi.resetModules();
  vi.stubEnv("NEXT_PUBLIC_FIREBASE_PROJECT_ID", projectId); // "" = unset (falsy), never leaks the real env
  return await import("../log");
}

beforeEach(() => {
  vi.useFakeTimers();
  fetchMock = vi.fn().mockResolvedValue({ ok: true });
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("log transport", () => {
  it("is a no-op when NEXT_PUBLIC_FIREBASE_PROJECT_ID is unset", async () => {
    const { logEvent } = await freshLog("");
    logEvent("search", { query: "q" });
    vi.advanceTimersByTime(3000);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("batches events within 2s into one commit with keepalive", async () => {
    const { logEvent } = await freshLog(PROJECT);
    logEvent("search", { query: "բարեւ", resultCount: 3, source: "home" });
    logEvent("open", { sketchId: "abc123" });
    vi.advanceTimersByTime(2100);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(url(fetchMock.mock.calls)).toBe(
      `https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents:commit`,
    );
    expect(fetchMock.mock.calls[0][1].keepalive).toBe(true);
    const writes = body(fetchMock.mock.calls).writes;
    expect(writes).toHaveLength(2);
    expect(writes[0].update.name).toMatch(
      new RegExp(`^projects/${PROJECT}/databases/\\(default\\)/documents/events/[0-9a-f-]{36}$`),
    );
    expect(writes[0].currentDocument).toEqual({ exists: false });
    expect(writes[0].updateTransforms).toEqual([{ fieldPath: "ts", setToServerValue: "REQUEST_TIME" }]);
    const f = writes[0].update.fields;
    expect(f.type).toEqual({ stringValue: "search" });
    expect(f.query).toEqual({ stringValue: "բարեւ" });
    expect(f.resultCount).toEqual({ integerValue: "3" });
    expect(f.sessionId.stringValue.length).toBeGreaterThan(0);
    expect(f.ua.stringValue.length).toBeLessThanOrEqual(256);
    expect(f.ts).toBeUndefined(); // ts comes only from the server transform
  });

  it("clamps oversized fields to the rules contract", async () => {
    const { logEvent } = await freshLog(PROJECT);
    logEvent("search", { query: "x".repeat(600), filters: { loc: ["y".repeat(2000)] } });
    vi.advanceTimersByTime(2100);
    const f = body(fetchMock.mock.calls).writes[0].update.fields;
    expect(f.query.stringValue).toHaveLength(500);
    expect(f.filters.stringValue.length).toBeLessThanOrEqual(1000);
    expect(typeof f.filters.stringValue).toBe("string"); // filters is a JSON string by contract
  });

  it("drops undefined fields instead of encoding them", async () => {
    const { logEvent } = await freshLog(PROJECT);
    logEvent("copy", { sketchId: "abc" });
    vi.advanceTimersByTime(2100);
    const f = body(fetchMock.mock.calls).writes[0].update.fields;
    expect(f.query).toBeUndefined();
    expect(f.filters).toBeUndefined();
  });

  it("never throws when fetch fails", async () => {
    fetchMock.mockRejectedValue(new Error("network down"));
    const { logEvent } = await freshLog(PROJECT);
    expect(() => {
      logEvent("search", { query: "q" });
      vi.advanceTimersByTime(2100);
    }).not.toThrow();
  });
});
```

Run in `web/`: `npx vitest run lib/__tests__/log.test.ts` → expect FAIL (module still posts to `LOG_ENDPOINT`).

- [ ] **Step 2: Rewrite `web/lib/log.ts`** (public API `logEvent(type, payload)` unchanged — callers untouched):

```ts
/**
 * Anonymous usage logging — batches events and writes them straight to
 * Firestore's REST commit endpoint with fetch(keepalive). No SDK: security
 * lives in firestore.rules (create-only, shape-validated), and keepalive
 * preserves delivery when the tab closes. No-op until the build sets
 * NEXT_PUBLIC_FIREBASE_PROJECT_ID, and on the server (SSR). No personal data.
 * Clamps mirror the rules contract — a rules rejection means a bug, and the
 * whole batch is dropped with a console.warn (fine for telemetry).
 */
export type LogType = "search" | "open" | "filter" | "findname" | "copy";

interface LogEvent {
  sessionId: string;
  type: LogType;
  query?: string;
  mode?: string;
  filters?: unknown;
  resultCount?: number;
  sketchId?: string;
  source?: string;
}

function projectId(): string | undefined {
  return process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID;
}

function sessionId(): string {
  try {
    let id = sessionStorage.getItem("kargin_sid");
    if (!id) {
      id = crypto.randomUUID();
      sessionStorage.setItem("kargin_sid", id);
    }
    return id;
  } catch (e) {
    console.warn("kargin log: sessionId unavailable", e);
    return "anon";
  }
}

type FsValue = { stringValue: string } | { integerValue: string };

/** Clamp to the firestore.rules contract and encode as Firestore REST values. */
function toFields(e: LogEvent): Record<string, FsValue> {
  const s = (v: string, max: number): FsValue => ({ stringValue: v.slice(0, max) });
  const fields: Record<string, FsValue> = {
    sessionId: s(e.sessionId, 64),
    type: s(e.type, 32),
    ua: s(navigator.userAgent, 256),
  };
  if (e.query !== undefined) fields.query = s(e.query, 500);
  if (e.mode !== undefined) fields.mode = s(e.mode, 32);
  if (e.filters !== undefined) fields.filters = s(JSON.stringify(e.filters), 1000);
  if (e.resultCount !== undefined)
    // Always an integer: rules require `is int`, and one float would fail the whole batch.
    fields.resultCount = { integerValue: String(Math.trunc(e.resultCount)) };
  if (e.sketchId !== undefined) fields.sketchId = s(e.sketchId, 64);
  if (e.source !== undefined) fields.source = s(e.source, 32);
  return fields;
}

const queue: LogEvent[] = [];
let timer: ReturnType<typeof setTimeout> | null = null;

function flush(): void {
  timer = null;
  const pid = projectId();
  if (!pid || queue.length === 0) return;
  // 20 events × ~2 KB worst-case clamped fields ≈ 40 KB — keepalive bodies cap at 64 KB.
  const batch = queue.splice(0, 20);
  const docs = `projects/${pid}/databases/(default)/documents`;
  const writes = batch.map((e) => ({
    update: { name: `${docs}/events/${crypto.randomUUID()}`, fields: toFields(e) },
    currentDocument: { exists: false },
    updateTransforms: [{ fieldPath: "ts", setToServerValue: "REQUEST_TIME" }],
  }));
  try {
    void fetch(`https://firestore.googleapis.com/v1/${docs}:commit`, {
      method: "POST",
      body: JSON.stringify({ writes }),
      keepalive: true,
      headers: { "Content-Type": "application/json" },
    }).catch((e) => console.warn("kargin log: flush failed", e));
  } catch (e) {
    /* logging must never break the app, but the failure must be observable */
    console.warn("kargin log: flush failed", e);
  }
}

export function logEvent(type: LogType, payload: Omit<LogEvent, "sessionId" | "type"> = {}): void {
  if (!projectId() || typeof window === "undefined") return;
  queue.push({ sessionId: sessionId(), type, ...payload });
  if (!timer) timer = setTimeout(flush, 2000); // batch within 2s
}

if (typeof window !== "undefined") {
  // Flush whatever's queued when the tab is hidden/closed.
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") flush();
  });
}
```

- [ ] **Step 3: Run the new tests and the full web suite — expect PASS**: `npx vitest run lib/__tests__/log.test.ts`, then `npm test`, `npx tsc --noEmit`, `npm run lint`.

- [ ] **Step 4: Swap the CI build env var** in `.github/workflows/deploy.yml` — replace the `NEXT_PUBLIC_LOG_ENDPOINT` line on the `npm run build` step with:

```yaml
          NEXT_PUBLIC_FIREBASE_PROJECT_ID: ${{ vars.FIREBASE_PROJECT_ID }}
```

- [ ] **Step 5: Commit**

```bash
git add web/lib/log.ts web/lib/__tests__/log.test.ts .github/workflows/deploy.yml
git commit -m "feat(web): usage logging writes to Firestore via REST commit + keepalive"
```

### Task 9: verify, soak, decommission Worker + Neon (USER ACTIONS marked)

- [ ] **Step 1: Push; after deploy, verify live**: on `https://<project-id>.web.app`, run a search, wait ~5 s, confirm the event doc appears in the Firestore console `events` collection with a server `ts`.
- [ ] **Step 2: Soak ≥ 3 days.** Stale tabs holding the old bundle keep posting to the Worker; let them drain. Spot-check that new events keep arriving in Firestore.
- [ ] **Step 3 (USER): export Neon last, right before deletion** — from the Neon SQL editor or `psql`:

```sql
\copy (select * from query_log order by ts) to 'query_log_backup.csv' with csv header
```

Save to `internal/neon_export/query_log_backup.csv` (gitignored — usage logs don't belong in a public repo).
- [ ] **Step 4 (USER): delete the Worker** (`npx wrangler delete` in `logger-worker/`, or Cloudflare dashboard) **and the Neon project.**
- [ ] **Step 5: Archive the worker code**:

```bash
git mv logger-worker old/logger-worker
```

Prepend to `old/logger-worker/README.md`: `> DECOMMISSIONED 2026-MM-DD — replaced by direct Firestore writes (see docs/superpowers/specs/2026-09-06-firebase-migration-design.md). Kept as institutional record.` Commit:

```bash
git add -A && git commit -m "chore: decommission logger-worker (replaced by Firestore events)"
```

**Phase 3 exit:** events flowing to Firestore from the live site; Worker and Neon gone; backup CSV saved.

---

## Phase 4 — Domain cutover

### Task 10: move `karginhaghordum.am`, retire Pages (USER ACTIONS marked)

- [ ] **Step 1 (USER): Firebase console → Hosting → Add custom domain → `karginhaghordum.am`, choosing "Advanced setup"** — this provisions the TLS cert *before* traffic moves (no HTTPS-error window). Complete the TXT verification records it asks for.
- [ ] **Step 2 (USER): wait until the console shows the cert issued, then flip the A/AAAA records** at the registrar to the Firebase IPs it lists. Also add the `www` subdomain if currently served.
- [ ] **Step 3: verify from the outside**: `curl -sI https://karginhaghordum.am/ | head -5` → 200 with a valid cert; spot-check a sketch page and search.
- [ ] **Step 4: wait out the old DNS TTL (days, not minutes)** — GitHub Pages keeps serving stale-cache visitors meanwhile. Don't touch Pages yet.
- [ ] **Step 5: retire Pages** — in `.github/workflows/deploy.yml` delete the `upload-pages-artifact` step, the whole `deploy` job, and the now-unused `permissions: pages/id-token` entries; delete `web/public/CNAME` and `web/public/.nojekyll`; disable Pages in repo Settings. Run `npm run build` in `web/` once to confirm nothing referenced the removed files. Commit:

```bash
git add -A && git commit -m "chore: retire GitHub Pages — karginhaghordum.am now served by Firebase Hosting"
```

- [ ] **Step 6: close the loop** — update `PROGRESS.md` (migration done), add a `LEARNINGS.md` entry for anything non-obvious hit along the way, and mark the spec's status line `implemented`.

**Phase 4 exit:** domain serves from Firebase with a valid cert; Pages disabled; repo has no Pages leftovers.
