import { describe, expect, it } from "vitest";
import {
  cardKeyboard, cardText, escapeHtml, EXAMPLES, inlineDescription, moreCallback, PAGE,
  resultsMessage, searchTop, siteUrl, startKeyboard, startText,
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

describe("resultsMessage", () => {
  const many = Array.from({ length: 15 }, (_, i) =>
    sketch({ id: `id${i}aaaaaaaa`, title: `Սքեթչ ${i}`, textCommon: i === 0 ? "հայտնի տող" : "" }));

  it("lists each result with a hook line and numbers the buttons", () => {
    const { text, keyboard } = resultsMessage("test", many, 0);
    expect(text).toContain("«test» — 15 արդյունք");
    expect(text).toContain("<b>1.</b> Սքեթչ 0");
    expect(text).toContain("★ «հայտնի տող»");    // famous line as the hook
    expect(text).toContain("👥 Հայկո, Մկո");      // actors fallback hook
    const rows = keyboard.inline_keyboard;
    expect(rows[0].map((b) => b.text)).toEqual(["1", "2", "3", "4", "5", "6"]);
    expect((rows[0][0] as { callback_data: string }).callback_data).toBe("s:id0aaaaaaaa");
    expect((rows[1][0] as { switch_inline_query_current_chat: string }).switch_inline_query_current_chat).toBe("test");
    expect(rows[1][1].text).toBe(`➕ Ավելին (${15 - PAGE})`);
  });

  it("offsets numbering and drops the more-button on the last page", () => {
    const { text, keyboard } = resultsMessage("test", many, 12);
    expect(text).toContain("<b>13.</b> Սքեթչ 12");
    expect(keyboard.inline_keyboard[0].map((b) => b.text)).toEqual(["13", "14", "15"]);
    expect(keyboard.inline_keyboard[1].map((b) => b.text)).toEqual(["🖼 Նկարներով"]);
  });

  it("never emits callback_data over Telegram's 64-byte cap", () => {
    expect(moreCallback("տոռմուզ", 6)).toBe("m:6:տոռմուզ");
    expect(moreCallback("ա".repeat(40), 6)).toBeNull(); // 80+ bytes of Armenian
    const { keyboard } = resultsMessage("ա".repeat(40), many, 0);
    expect(keyboard.inline_keyboard[1].map((b) => b.text)).toEqual(["🖼 Նկարներով"]); // more-button dropped
  });

  it("zero results gets typed search tips and a random button", () => {
    const { text, keyboard } = resultsMessage("xyz", [], 0);
    expect(text).toContain("Ոչինչ չգտնվեց");
    expect(text).toContain("📍 վայր");
    expect((keyboard.inline_keyboard[0][0] as { callback_data: string }).callback_data).toBe("r");
  });
});

describe("card keyboard", () => {
  it("offers site, share-via-inline, and rethrow", () => {
    const rows = cardKeyboard(sketch({ title: "Տոռմուզի սքեթչ" })).inline_keyboard;
    expect(rows).toHaveLength(2);
    expect((rows[0][0] as { url: string }).url).toBe("https://karginhaghordum.am/sketch/abc123def45/");
    expect((rows[0][1] as { switch_inline_query: string }).switch_inline_query).toBe("Տոռմուզի սքեթչ");
    expect((rows[1][0] as { callback_data: string }).callback_data).toBe("r");
  });
});

describe("start", () => {
  it("names the actual bot username for inline usage", () => {
    expect(startText("KarginSearchBot")).toContain("@KarginSearchBot");
  });
  it("keyboard has one-tap typed example searches plus random and site", () => {
    const rows = startKeyboard().inline_keyboard;
    expect(rows).toHaveLength(3); // 3 examples + 2 examples + actions
    const callbacks = [...rows[0], ...rows[1]].map((b) => (b as { callback_data: string }).callback_data);
    expect(callbacks).toEqual(EXAMPLES.map((e) => `q:${e.q}`));
    expect((rows[2][0] as { callback_data: string }).callback_data).toBe("r");
    expect((rows[2][1] as { url: string }).url).toBe("https://karginhaghordum.am");
  });
  it("every example search actually returns results", () => {
    for (const e of EXAMPLES) expect(searchTop(e.q).length, e.q).toBeGreaterThan(0);
  });
});

describe("inlineDescription", () => {
  it("leads with the famous line when there is one, else the actors", () => {
    expect(inlineDescription(sketch({ textCommon: "ուր ես գնում" }))).toContain("«ուր ես գնում»");
    expect(inlineDescription(sketch())).toContain("Հայկո, Մկո");
    expect(inlineDescription(sketch())).toContain("⏱ 3:05 · 👁 1.2M · Բակ");
  });
});

describe("texts", () => {
  it("site url points at the canonical domain", () => {
    expect(siteUrl(sketch())).toBe("https://karginhaghordum.am/sketch/abc123def45/");
  });
});
