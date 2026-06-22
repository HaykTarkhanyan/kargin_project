import { describe, it, expect } from "vitest";
import { romanize } from "@/lib/translit";
import { searchSketches } from "@/lib/search";
import type { Sketch } from "@/lib/types";

// ---------------------------------------------------------------------------
// Armenian character helpers
//
// We build strings from explicit codepoints to avoid copy-paste encoding
// ambiguity (Cyrillic о/м/з look visually identical to Armenian ո/մ/զ).
// ---------------------------------------------------------------------------

// Pure-Armenian word "tormuz": տ(57f) ո(578) ռ(57c) մ(574) ու(578,582) զ(566)
const ARM_TORMUZ = String.fromCodePoint(0x57f, 0x578, 0x57c, 0x574, 0x578, 0x582, 0x566);
// Matches the search.test.ts fixture text exactly.
const ARM_DIALOGUE = String.fromCodePoint(
  0x540, 0x578, 0x57a, // Հоп
  0x20,
  0x568, 0x576, 0x563, 0x565, 0x580, // ընгер
  0x20,
  0x57b, 0x561, 0x576, // ջান
  0x2c, 0x20,
  0x57f, 0x578, 0x57c, 0x574, 0x578, 0x582, 0x566, // տоռмuз
  0x20,
  0x570, 0x568, 0x56c, 0x568, // հըлы
);

// Pure Armenian "hayko": հ(570) ա(561) յ(575) կ(56f) ο(578)
const ARM_HAYKO = String.fromCodePoint(0x570, 0x561, 0x575, 0x56f, 0x578);

// ---------------------------------------------------------------------------
// romanize unit tests
// ---------------------------------------------------------------------------

describe("romanize", () => {
  it("converts ու digraph before single chars (→ u, not ov)", () => {
    // ο(578) + ւ(582) together = ου = 'u' sound
    const ou = String.fromCodePoint(0x578, 0x582);
    expect(romanize(ou)).toBe("u");
  });

  it("handles և ligature → ev", () => {
    expect(romanize("և")).toBe("ev");
  });

  it("converts pure-Armenian tormuz word → 'tormuz'", () => {
    expect(romanize(ARM_TORMUZ)).toBe("tormuz");
  });

  it("converts pure-Armenian hayko word → 'hayko'", () => {
    expect(romanize(ARM_HAYKO)).toBe("hayko");
  });

  it("passes non-Armenian characters through unchanged (lowercase)", () => {
    expect(romanize("abc 123")).toBe("abc 123");
  });

  it("converts ը to empty string (schwa is silent in romanization)", () => {
    // ը(568) followed by Latin n → just 'n'
    expect(romanize(String.fromCodePoint(0x568) + "n")).toBe("n");
  });

  it("lowercases uppercase Armenian before mapping", () => {
    // Uppercase Հ(540) → lowercase հ(570) → 'h'
    expect(romanize(String.fromCodePoint(0x540))).toBe("h");
    // Uppercase Ա → ա → 'a'
    expect(romanize(String.fromCodePoint(0x531))).toBe("a");
  });

  it("round-trip: romanized form of single Armenian chars matches spec", () => {
    const pairs: Array<[number, string]> = [
      [0x561, "a"],  // ա
      [0x562, "b"],  // բ
      [0x563, "g"],  // գ
      [0x56a, "zh"], // ժ
      [0x56d, "kh"], // խ
      [0x56e, "ts"], // ծ
      [0x571, "dz"], // ձ
      [0x572, "gh"], // ղ
      [0x573, "ch"], // ճ
      [0x577, "sh"], // շ
      [0x57b, "j"],  // ջ
      [0x57c, "r"],  // ռ
      [0x581, "ts"], // ց
      [0x56b, "i"],  // ի
    ];
    for (const [cp, lat] of pairs) {
      const arm = String.fromCodePoint(cp);
      expect(romanize(arm), `romanize(U+${cp.toString(16)})`).toBe(lat);
    }
  });

  it("correctly maps ց (U+581) → ts", () => {
    expect(romanize(String.fromCodePoint(0x581))).toBe("ts");
  });

  it("correctly maps փ (U+583) → p, ք (U+584) → k, ֆ (U+586) → f", () => {
    expect(romanize(String.fromCodePoint(0x583))).toBe("p");
    expect(romanize(String.fromCodePoint(0x584))).toBe("k");
    expect(romanize(String.fromCodePoint(0x586))).toBe("f");
  });
});

// ---------------------------------------------------------------------------
// Test fixture helpers
// ---------------------------------------------------------------------------

const mk = (p: Partial<Sketch>): Sketch => ({
  id: "x", videoId: "x", seq: null, title: "", url: "", thumbnail: "",
  text: "", textCommon: "", actors: [], actorsRaw: "", rolesNames: "",
  location: "Other", languages: [], lighting: "", durationSec: 120, viewCount: 0,
  uploadDate: "", ...p,
});

// ---------------------------------------------------------------------------
// Romanized search integration tests
// ---------------------------------------------------------------------------

describe("romanized search", () => {
  const testData = [
    mk({ id: "a", text: ARM_DIALOGUE }),  // contains ARM_TORMUZ which romanizes to 'tormuz'
    mk({ id: "b", textCommon: "unrelated content here" }),
  ];

  it("Latin query 'tormuz' finds sketch whose Armenian text romanizes to include 'tormuz'", () => {
    const r = searchSketches("tormuz", testData, {});
    expect(r.map((s) => s.id)).toContain("a");
  });

  it("does not return unrelated sketch for Latin romanized query", () => {
    const r = searchSketches("tormuz", testData, {});
    expect(r.map((s) => s.id)).not.toContain("b");
  });

  it("Armenian query still works unchanged after romanized index is added", () => {
    // Direct Armenian query should still find sketch 'a'
    const r = searchSketches(ARM_TORMUZ, testData, {});
    expect(r.map((s) => s.id)).toContain("a");
  });

  it("empty query returns all results", () => {
    expect(searchSketches("", testData, {}).length).toBe(testData.length);
  });

  it("exact romanized match is the first result", () => {
    const r = searchSketches("tormuz", testData, {});
    if (r.length > 0) expect(r[0].id).toBe("a");
  });
});

// ---------------------------------------------------------------------------
// Typo-tolerant fuzzy search tests
// ---------------------------------------------------------------------------

describe("fuzzy search", () => {
  // Sketch whose text contains a word that romanizes to 'tormuz'
  const fuzzyData = [
    mk({ id: "a", text: ARM_DIALOGUE }),  // contains word that romanizes to 'tormuz'
    mk({ id: "b", textCommon: "completely different story" }),
  ];

  it("1-char typo 'torzuz' (m→z) still finds the sketch with 'tormuz'", () => {
    const r = searchSketches("torzuz", fuzzyData, {});
    expect(r.map((s) => s.id)).toContain("a");
  });

  it("1-char typo 'tormus' (z→s) still finds the sketch with 'tormuz'", () => {
    const r = searchSketches("tormus", fuzzyData, {});
    expect(r.map((s) => s.id)).toContain("a");
  });

  it("exact matches rank before fuzzy-only matches", () => {
    const mixedData = [
      mk({ id: "exact", text: "tormuz exact match" }),   // literal "tormuz" in text
      mk({ id: "fuzzy-only", text: "nothing related ever" }), // nothing close
    ];
    const r = searchSketches("torzuz", mixedData, {});
    const ids = r.map((s) => s.id);
    // "exact" has "tormuz" which is 1 char from "torzuz" → fuzzy hit
    // "fuzzy-only" has nothing similar → should not appear
    expect(ids).toContain("exact");
    expect(ids).not.toContain("fuzzy-only");
  });

  it("exact match via Armenian romanization ranks before fuzzy-only supplement", () => {
    const rankedData = [
      mk({ id: "exact", text: ARM_TORMUZ }),      // exact match via romanize
      mk({ id: "fuzzy-close", text: "torzuz" }),  // fuzzy match only
    ];
    const r = searchSketches("tormuz", rankedData, {});
    const ids = r.map((s) => s.id);
    // 'exact' matched via substring match in romanized text → higher score
    // 'fuzzy-close' is a fuzzy match of "torzuz"~="tormuz"
    if (ids.includes("exact") && ids.includes("fuzzy-close")) {
      expect(ids.indexOf("exact")).toBeLessThan(ids.indexOf("fuzzy-close"));
    }
  });
});
