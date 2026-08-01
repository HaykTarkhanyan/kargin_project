import { describe, it, expect } from "vitest";
import { textLines, segmentsFor, matchedFirst } from "@/lib/segments";

describe("textLines", () => {
  it("splits on ';' and the Armenian full stop, trimming empties", () => {
    expect(textLines("բարև; ոնց ես։ լավ")).toEqual(["բարև", "ոնց ես", "լավ"]);
  });
  it("does not split on '-' (would mangle '1-2')", () => {
    expect(textLines("1-2 1-2")).toEqual(["1-2 1-2"]);
  });
  it("returns [] for empty text", () => {
    expect(textLines("")).toEqual([]);
  });
});

describe("segmentsFor", () => {
  const text = "բարև ձեզ; ոնց ես ախպեր; վերջին տողը";

  it("marks nothing when there is no query", () => {
    const segs = segmentsFor(text, "");
    expect(segs).toHaveLength(3);
    expect(segs.every((s) => !s.matched && s.hits.length === 0)).toBe(true);
  });

  it("flags the matching line and gives offsets into the ORIGINAL text", () => {
    const segs = segmentsFor(text, "ախպեր");
    expect(segs.map((s) => s.matched)).toEqual([false, true, false]);
    const hit = segs[1];
    expect(hit.hits).toHaveLength(1);
    const [start, end] = hit.hits[0];
    expect(hit.text.slice(start, end)).toBe("ախպեր");
  });

  it("finds every occurrence in a line", () => {
    const segs = segmentsFor("բարև բարև բարև", "բարև");
    expect(segs[0].hits).toHaveLength(3);
  });

  it("is case-insensitive", () => {
    const segs = segmentsFor("Բարև ձեզ", "բարև");
    expect(segs[0].matched).toBe(true);
    const [start, end] = segs[0].hits[0];
    expect(segs[0].text.slice(start, end)).toBe("Բարև");
  });

  it("matches a Latin query against Armenian, without bogus offsets", () => {
    // romanize changes length, so an offset in the romanized string would not
    // map back — the line is flagged but carries no inner highlight.
    const segs = segmentsFor("բարև ձեզ", "barev");
    expect(segs[0].matched).toBe(true);
    expect(segs[0].hits).toEqual([]);
  });

  it("does not flag lines that do not match", () => {
    expect(segmentsFor(text, "ուզբեկ").every((s) => !s.matched)).toBe(true);
  });
});

describe("matchedFirst", () => {
  it("floats matches up, preserving order within each group", () => {
    const segs = segmentsFor("ա; բարև; բ; բարև գ", "բարև");
    const ordered = matchedFirst(segs);
    expect(ordered.map((s) => s.text)).toEqual(["բարև", "բարև գ", "ա", "բ"]);
  });

  it("leaves order untouched when nothing matched", () => {
    const segs = segmentsFor("ա; բ; գ", "ուզբեկ");
    expect(matchedFirst(segs).map((s) => s.text)).toEqual(["ա", "բ", "գ"]);
  });
});
