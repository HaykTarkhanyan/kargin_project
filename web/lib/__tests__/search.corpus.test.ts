/**
 * Regression test against the real corpus, from real usage data.
 *
 * On 2026-09-11 the Firestore `events` log showed 13 of ~56 distinct site
 * queries returning nothing, almost all of them multi-word: visitors typing a
 * line they remembered. These are those queries. They are kept here rather than
 * as synthetic fixtures because the failure depended on the actual punctuation
 * and phrasing of the archive, which no fixture would reproduce.
 *
 * `sketches.json` is built from the CSV before this runs (locally by the build,
 * in CI by the "Build site data" step).
 */
import { describe, it, expect, beforeAll } from "vitest";
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { searchSketches } from "@/lib/search";
import type { Sketch } from "@/lib/types";

const DATA = join(process.cwd(), "public/data/sketches.json");
const ALL: Sketch[] = existsSync(DATA) ? JSON.parse(readFileSync(DATA, "utf-8")) : [];

describe.skipIf(ALL.length === 0)("real corpus regressions", () => {
  // The first query over the real corpus builds every per-sketch index and the
  // fuzzy vocabulary. That is one-time work, not per-query cost, so it happens
  // here rather than inside whichever test ran first.
  beforeAll(() => { searchSketches("բարև ձեզ", ALL, {}); }, 60_000);

  // Every word of these is somewhere in the sketch; only the punctuation and
  // filler between them differ from what the visitor typed.
  it.each([
    "լավ կառնեմ էտ",
    "պապա պտի ասես",
    "էտքանը որ անում",
    "էտքանը որ անում եմ",
  ])("finds something for %s, which used to return nothing", (q) => {
    expect(searchSketches(q, ALL, {}).length).toBeGreaterThan(0);
  });

  it("puts the sketch that actually says the rarest word first", () => {
    // Asserted on the text rather than an id, so re-running the build pipeline
    // cannot break this on a sketch that still answers the query correctly.
    const top = searchSketches("էտքանը որ անում եմ", ALL, {})[0];
    const said = `${top.text} ${top.transcript?.text ?? ""}`.toLowerCase();
    expect(said).toContain("էտքանը");
  });

  it("does not invent matches for a line the archive does not contain", () => {
    // "բուդելնիկն ա երկու հատ" — the archive says "բուդելնիկա դրած", and none of
    // the remaining words are distinctive. Returning nothing beats 132 guesses.
    expect(searchSketches("բուդելնիկն ա երկու հատ", ALL, {}).length).toBeLessThan(20);
  });

  it("still answers a literal phrase from the exact pass", () => {
    const r = searchSketches("տոռմուզ", ALL, {});
    expect(r.length).toBeGreaterThan(0);
  });

  // The old code spent 1.6-3.2 s per multi-word query by fuzzy-expanding every
  // word of the phrase. This guards the pass from drifting back into that.
  it("answers a long phrase quickly", () => {
    searchSketches("warmup", ALL, {}); // build the indexes outside the measurement
    const t = Date.now();
    searchSketches("էտքանը որ անում եմ ախպեր ջան", ALL, {});
    expect(Date.now() - t).toBeLessThan(1000);
  });
});
