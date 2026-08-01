import { describe, it, expect } from "vitest";
import { CHANGELOG } from "@/lib/changelog";

describe("CHANGELOG", () => {
  it("is not empty and every entry has items", () => {
    expect(CHANGELOG.length).toBeGreaterThan(0);
    for (const e of CHANGELOG) expect(e.items.length).toBeGreaterThan(0);
  });

  it("uses ISO dates", () => {
    for (const e of CHANGELOG) expect(e.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("is ordered newest first", () => {
    const dates = CHANGELOG.map((e) => e.date);
    expect([...dates].sort().reverse()).toEqual(dates);
  });

  it("every item has an icon and non-empty text", () => {
    for (const e of CHANGELOG) {
      for (const item of e.items) {
        expect(item.icon.length).toBeGreaterThan(0);
        expect(item.text.trim().length).toBeGreaterThan(0);
      }
    }
  });

  it("only uses count keys the page knows how to render", () => {
    const known = new Set(["songs", "sketchesWithSongs", "sketches", "withText"]);
    for (const e of CHANGELOG) {
      for (const item of e.items) {
        if (item.count) expect(known.has(item.count)).toBe(true);
      }
    }
  });
});
