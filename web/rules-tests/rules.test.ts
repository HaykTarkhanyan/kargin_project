/**
 * Firestore security-rules tests. These run against the emulator, not jsdom:
 *   npm run test:rules
 * (wraps `vitest run --config vitest.rules.config.ts` in `firebase emulators:exec`).
 */
import { readFileSync } from "node:fs";
import { afterAll, beforeAll, describe, it } from "vitest";
import {
  assertFails,
  assertSucceeds,
  initializeTestEnvironment,
  type RulesTestEnvironment,
} from "@firebase/rules-unit-testing";
import {
  collection,
  deleteDoc,
  doc,
  getDoc,
  getDocs,
  serverTimestamp,
  setDoc,
  updateDoc,
} from "firebase/firestore";

let env: RulesTestEnvironment;

beforeAll(async () => {
  const [host, port] = (process.env.FIRESTORE_EMULATOR_HOST ?? "127.0.0.1:8080").split(":");
  env = await initializeTestEnvironment({
    projectId: "demo-kargin",
    firestore: { host, port: Number(port), rules: readFileSync("firestore.rules", "utf8") },
  });
});
afterAll(async () => {
  await env.cleanup();
});

const anon = () => env.unauthenticatedContext().firestore();
const valid = () => ({
  sessionId: "s1",
  type: "search",
  query: "բարեւ",
  resultCount: 3,
  source: "home",
  ua: "test",
  ts: serverTimestamp(),
});

describe("events", () => {
  it("accepts a valid anonymous create", async () => {
    await assertSucceeds(setDoc(doc(anon(), "events", "e1"), valid()));
  });
  it("accepts a share event", async () => {
    await assertSucceeds(
      setDoc(doc(anon(), "events", "e1b"), { ...valid(), type: "share", query: "telegram" }),
    );
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
      setDoc(doc(ctx.firestore(), "events", "seed"), { sessionId: "s", type: "open" }),
    );
    await assertFails(getDocs(collection(anon(), "events")));
    await assertFails(updateDoc(doc(anon(), "events", "seed"), { type: "copy" }));
    await assertFails(deleteDoc(doc(anon(), "events", "seed")));
  });
});

describe("sketches", () => {
  it("allows public read, denies client write", async () => {
    await env.withSecurityRulesDisabled(async (ctx) =>
      setDoc(doc(ctx.firestore(), "sketches", "abc"), { title: "t" }),
    );
    await assertSucceeds(getDoc(doc(anon(), "sketches", "abc")));
    await assertFails(setDoc(doc(anon(), "sketches", "zzz"), { title: "nope" }));
  });
});
