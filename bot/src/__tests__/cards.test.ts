import { describe, expect, it } from "vitest";
import {
  cardText, escapeHtml, moreCallback, PAGE, resultsKeyboard, resultsText, searchTop, siteUrl,
} from "../cards";
import { ALL, byId, randomSketch } from "../data";
import type { Sketch } from "../../../web/lib/types";

const sketch = (over: Partial<Sketch> = {}): Sketch => ({
  id: "abc123def45", videoId: "abc123def45", seq: 1, title: "Տեստ <սքեթչ>",
  url: "https://youtu.be/abc123def45", thumbnail: "https://i.ytimg.com/vi/abc123def45/hq.jpg",
  text: "", textCommon: "", actors: ["Հայկո", "Մկո"], actorsRaw: "", rolesNames: "",
  location: "Բակ", languages: ["hy"], lighting: "", durationSec: 185, viewCount: 1_200_000,
  uploadDate: "2013-01-01", ...over,
});

describe("data (shared artifact)", () => {
  it("loads the full corpus with unique ids", () => {
    expect(ALL.length).toBeGreaterThan(700);
    expect(byId(ALL[0].id)?.id).toBe(ALL[0].id);
    expect(ALL.map((s) => s.id)).toContain(randomSketch().id);
  });
});

describe("shared search through the bot path", () => {
  // 30s budget: the first sparse query builds the fuzzy word index for the
  // whole corpus (romanize + cyrillize 702 sketches) — slow on a laptop, once.
  it("Latin transliteration finds every sketch the Armenian query finds", { timeout: 30000 }, () => {
    const hy = searchTop("տոռմուզ").map((s) => s.id);
    const lat = new Set(searchTop("tormuz").map((s) => s.id));
    expect(hy.length).toBeGreaterThan(0);
    // Superset, not equality: ambiguous transliteration (ո→o, ռ/ր→r) legitimately
    // lets the Latin form match additional sketches — same behavior as the site.
    for (const id of hy) expect(lat.has(id)).toBe(true);
  });
  it("empty query returns everything, most-viewed first", () => {
    const all = searchTop("");
    expect(all.length).toBe(ALL.length);
    expect((all[0].viewCount ?? 0) >= (all[1].viewCount ?? 0)).toBe(true);
  });
});

describe("cardText", () => {
  it("escapes HTML, shows the famous line, links youtu.be", () => {
    const t = cardText(sketch({ textCommon: "«մեջբերում» & <b>" }));
    expect(t).toContain("Տեստ &lt;սքեթչ&gt;");
    expect(t).toContain("★ ««մեջբերում» &amp; &lt;b&gt;»");
    expect(t).toContain("https://youtu.be/abc123def45");
    expect(t).toContain("⏱ 3:05 · 👁 1.2M");
  });
  it("omits the famous-line block when there is none", () => {
    expect(cardText(sketch())).not.toContain("★");
  });
});

describe("keyboards", () => {
  const many = Array.from({ length: 15 }, (_, i) =>
    sketch({ id: `id${i}aaaaaaaa`, title: `Սքեթչ ${i}` }));

  it("shows one page of results plus a counted more-button", () => {
    const rows = resultsKeyboard(many, "test", 0).inline_keyboard;
    expect(rows).toHaveLength(PAGE + 1);
    expect(rows[0][0].text).toContain("1. Սքեթչ 0");
    expect((rows[0][0] as { callback_data: string }).callback_data).toBe("s:id0aaaaaaaa");
    expect(rows[PAGE][0].text).toBe(`➕ Ավելին (${15 - PAGE})`);
  });

  it("omits the more-button on the last page and offsets numbering", () => {
    const rows = resultsKeyboard(many, "test", 12).inline_keyboard;
    expect(rows).toHaveLength(3);
    expect(rows[0][0].text).toContain("13. Սքեթչ 12");
  });

  it("never emits callback_data over Telegram's 64-byte cap", () => {
    expect(moreCallback("տոռմուզ", 6)).toBe("m:6:տոռմուզ");
    expect(moreCallback("ա".repeat(40), 6)).toBeNull(); // 80+ bytes of Armenian
    const rows = resultsKeyboard(many, "ա".repeat(40), 0).inline_keyboard;
    expect(rows).toHaveLength(PAGE); // more-button silently dropped, results intact
  });
});

describe("texts", () => {
  it("zero results gets tips, hits get a count", () => {
    expect(resultsText("xyz", 0)).toContain("Ոչինչ չգտնվեց");
    expect(resultsText("տոռմուզ", 7)).toBe("🔍 «տոռմուզ» — 7 արդյունք");
  });
  it("site url points at the canonical domain", () => {
    expect(siteUrl(sketch())).toBe("https://karginhaghordum.am/sketch/abc123def45/");
  });
});
