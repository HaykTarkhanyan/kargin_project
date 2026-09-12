import { describe, it, expect } from "vitest";
import {
  allCollections, collectionBySlug, collectionsForSketch, sketchesFor,
} from "@/lib/collections";

// Runs against the real collections.json, so it guards the curated data as well
// as the code: a slug that stops resolving, or a member that leaves the payload,
// fails here rather than on the deployed page.
describe("collections", () => {
  it("each have an ascii slug, copy, and unique members", () => {
    const all = allCollections();
    expect(all.length).toBeGreaterThan(0);
    for (const c of all) {
      expect(c.slug).toMatch(/^[a-z0-9_]+$/);
      expect(c.name.trim()).not.toBe("");
      expect(c.description.trim()).not.toBe("");
      expect(c.sketchIds.length).toBeGreaterThan(0);
      expect(new Set(c.sketchIds).size).toBe(c.sketchIds.length);
    }
  });

  it("have unique slugs", () => {
    const slugs = allCollections().map((c) => c.slug);
    expect(new Set(slugs).size).toBe(slugs.length);
  });

  it("resolve every member to a real sketch, most viewed first", () => {
    for (const c of allCollections()) {
      // Throws if an id is missing from sketches.json, which is the point.
      const sketches = sketchesFor(c.slug);
      expect(sketches).toHaveLength(c.sketchIds.length);
      const views = sketches.map((s) => s.viewCount ?? 0);
      expect(views).toEqual([...views].sort((a, b) => b - a));
    }
  });

  it("return nothing for an unknown slug instead of throwing", () => {
    expect(collectionBySlug("no_such_collection")).toBeUndefined();
    expect(sketchesFor("no_such_collection")).toEqual([]);
  });

  it("report every collection a sketch belongs to, including more than one", () => {
    const expected = new Map<string, string[]>();
    for (const c of allCollections()) {
      for (const id of c.sketchIds) expected.set(id, [...(expected.get(id) ?? []), c.slug]);
    }
    expect(expected.size).toBeGreaterThan(0);
    for (const [id, slugs] of expected) {
      expect(collectionsForSketch(id).map((c) => c.slug)).toEqual(slugs);
    }
    // The feature only earns the ';'-separated column if something uses it.
    expect([...expected.values()].some((slugs) => slugs.length > 1)).toBe(true);
  });

  it("know nothing about a sketch that is in no collection", () => {
    expect(collectionsForSketch("not-a-video-id")).toEqual([]);
  });
});
