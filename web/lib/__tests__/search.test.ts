import { describe, it, expect } from "vitest";
import { normalize, searchSketches } from "@/lib/search";
import { formatViews, formatDuration } from "@/lib/format";
import type { Sketch } from "@/lib/types";

const mk = (p: Partial<Sketch>): Sketch => ({
  id: "x", videoId: "x", seq: null, title: "", url: "", thumbnail: "",
  text: "", textCommon: "", actors: [], actorsRaw: "", rolesNames: "",
  location: "Այլ", languages: [], lighting: "", durationSec: 120, viewCount: 0,
  uploadDate: "", ...p,
});

describe("normalize", () => {
  it("lowercases and collapses whitespace", () => {
    expect(normalize("  ՏոՌմՈՒզ   հլը ")).toBe("տոռմուզ հլը");
  });
});

describe("searchSketches", () => {
  const data = [
    mk({ id: "a", title: "sketch 285", text: "Հոպ ընգեր ջան, տոռմուզ հըլը", location: "Տուն" }),
    mk({ id: "b", title: "sketch 108", textCommon: "լվացքի փոշի", location: "Խանութ" }),
  ];
  it("matches mid-word substring inside dialogue", () => {
    const r = searchSketches("տոռմուզ", data, {});
    expect(r.map((s) => s.id)).toEqual(["a"]);
  });
  it("returns all when query empty", () => {
    expect(searchSketches("", data, {}).length).toBe(2);
  });
  it("filters by location and composes with query", () => {
    expect(searchSketches("", data, { location: ["Խանութ"] }).map((s) => s.id)).toEqual(["b"]);
  });
  it("random sort returns the same set of results (no drops/dupes)", () => {
    expect(searchSketches("", data, {}, "random").map((s) => s.id).sort()).toEqual(["a", "b"]);
  });
});

describe("format", () => {
  it("formats views", () => { expect(formatViews(1358199)).toBe("1.4M"); expect(formatViews(813444)).toBe("813K"); });
  it("formats duration", () => { expect(formatDuration(242)).toBe("4:02"); });
});