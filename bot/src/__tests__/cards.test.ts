import { describe, expect, it } from "vitest";
import {
  cardKeyboard, cardText, decodeState, DURATIONS, encodeState, escapeHtml, EXAMPLES,
  inlineDescription, newState, PAGE, resultsMessage, runSearch, searchTop, siteUrl,
  startKeyboard, startText, type ViewState,
} from "../cards";
import { ACTORS, ALL, byId, LOCATIONS, randomSketch } from "../data";
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

describe("view state", () => {
  it("encode/decode round-trips; query may contain ':' or be empty", () => {
    const s: ViewState = { q: "ա:բ", loc: 1, actor: null, dur: 2, offset: 6 };
    expect(decodeState(encodeState(s))).toEqual(s);
    expect(decodeState(encodeState(newState("")))).toEqual(newState(""));
    expect(decodeState("garbage")).toBeNull();
  });
});

describe("resultsMessage", () => {
  const many = Array.from({ length: 15 }, (_, i) =>
    sketch({ id: `id${i}aaaaaaaa`, title: `Սքեթչ ${i}`, textCommon: i === 0 ? "հայտնի տող" : "" }));
  const st = (over: Partial<ViewState> = {}): ViewState => ({ ...newState("test"), ...over });

  it("lists each result with a hook line, number buttons, and the filter toggles", () => {
    const { text, keyboard } = resultsMessage(st(), many);
    expect(text).toContain("«test» — 15 արդյունք");
    expect(text).toContain("<b>1.</b> Սքեթչ 0");
    expect(text).toContain("★ «հայտնի տող»");    // famous line as the hook
    expect(text).toContain("👥 Հայկո, Մկո");      // actors fallback hook
    const rows = keyboard.inline_keyboard;
    expect(rows[0].map((b) => b.text)).toEqual(["1", "2", "3", "4", "5", "6"]);
    expect((rows[0][0] as { callback_data: string }).callback_data).toBe("s:id0aaaaaaaa");
    expect((rows[1][0] as { switch_inline_query_current_chat: string }).switch_inline_query_current_chat).toBe("test");
    expect((rows[1][1] as { callback_data: string }).callback_data).toBe(`v:-:-:-:${PAGE}:test`);
    expect(rows[2].map((b) => b.text)).toEqual(["📍 Վայր", "👤 Դերասան", "⏱ Տևողություն"]);
    expect((rows[2][0] as { callback_data: string }).callback_data).toBe("p:l:-:-:-:0:test");
  });

  it("offsets numbering and drops the more-button on the last page", () => {
    const { text, keyboard } = resultsMessage(st({ offset: 12 }), many);
    expect(text).toContain("<b>13.</b> Սքեթչ 12");
    expect(keyboard.inline_keyboard[0].map((b) => b.text)).toEqual(["13", "14", "15"]);
    expect(keyboard.inline_keyboard[1].map((b) => b.text)).toEqual(["🖼 Նկարներով"]);
  });

  it("shows active filters as header chips and in the toggle labels", () => {
    const tun = LOCATIONS.indexOf("Տուն");
    const state = st({ loc: tun, dur: 0 });
    const { text, keyboard } = resultsMessage(state, many);
    expect(text).toContain("· 📍 Տուն ·");
    expect(text).toContain("· ⏱ մինչև 2ր —");
    const toggles = keyboard.inline_keyboard[2].map((b) => b.text);
    expect(toggles).toEqual(["📍 Տուն", "👤 Դերասան", "⏱ մինչև 2ր"]);
  });

  it("panel lists values, checks the active one (tap = clear), pages keep filters", () => {
    const tun = LOCATIONS.indexOf("Տուն");
    const state = st({ loc: tun });
    const { keyboard } = resultsMessage(state, many, "l");
    const flat = keyboard.inline_keyboard.flat();
    expect(flat.find((b) => b.text === "📍 Տուն ▴")).toBeTruthy(); // open-panel marker
    const active = flat.find((b) => b.text === "✓ Տուն") as { callback_data: string };
    expect(active.callback_data).toBe("V:-:-:-:0:test");           // clears the filter
    const other = flat.find((b) => b.text === "Հիվանդանոց") as { callback_data: string };
    expect(other.callback_data).toBe(`V:${LOCATIONS.indexOf("Հիվանդանոց")}:-:-:0:test`);
    const more = flat.find((b) => b.text.startsWith("➕")) as { callback_data: string };
    expect(more.callback_data).toBe(`v:${tun}:-:-:${PAGE}:test`);  // paging keeps the filter
  });

  it("actor and duration panels index their own lists", () => {
    const a = resultsMessage(st(), many, "a").keyboard.inline_keyboard.flat();
    expect(a.find((b) => b.text === "Աշոտ")).toBeTruthy();
    const d = resultsMessage(st(), many, "d").keyboard.inline_keyboard.flat();
    const twoFour = d.find((b) => b.text === "2–4ր") as { callback_data: string };
    expect(twoFour.callback_data).toBe("V:-:-:1:0:test");
  });

  it("browse mode (empty query) gets its own header and keeps the toggles", () => {
    const { text, keyboard } = resultsMessage(newState(""), many);
    expect(text).toContain("🗂 Բոլոր սքեթչերը — 15 արդյունք");
    expect(keyboard.inline_keyboard[2].map((b) => b.text)).toEqual(["📍 Վայր", "👤 Դերասան", "⏱ Տևողություն"]);
  });

  it("drops over-budget buttons instead of emitting >64-byte callback_data", () => {
    const { keyboard } = resultsMessage(st({ q: "ա".repeat(40) }), many);
    const all = keyboard.inline_keyboard.flat() as Array<{ callback_data?: string }>;
    for (const b of all) if (b.callback_data) expect(Buffer.byteLength(b.callback_data, "utf8")).toBeLessThanOrEqual(64);
    expect(keyboard.inline_keyboard).toHaveLength(2); // numbers + 🖼 only; more/toggles dropped
  });

  it("zero results: typed tips when unfiltered, clear-all when filtered", () => {
    const plain = resultsMessage(st({ q: "xyz" }), []);
    expect(plain.text).toContain("Ոչինչ չգտնվեց");
    expect(plain.text).toContain("/browse");
    expect((plain.keyboard.inline_keyboard[0][0] as { callback_data: string }).callback_data).toBe("r");

    const filtered = resultsMessage(st({ q: "xyz", loc: 0, dur: 2 }), []);
    expect(filtered.text).toContain("Այս զտիչներով ոչինչ չգտնվեց");
    expect((filtered.keyboard.inline_keyboard[0][0] as { callback_data: string }).callback_data).toBe("v:-:-:-:0:xyz");
  });
});

describe("filtered search through the shared lib", () => {
  it("facet lists cover the corpus", () => {
    expect(LOCATIONS).toContain("Հիվանդանոց");
    expect(ACTORS).toContain("Մկո");
    expect(ACTORS.length).toBe(7);
  });
  it("each filter genuinely restricts, and they compose", () => {
    const all = runSearch(newState(""));
    const tun = runSearch({ ...newState(""), loc: LOCATIONS.indexOf("Տուն") });
    expect(tun.length).toBeGreaterThan(0);
    expect(tun.every((s) => s.location === "Տուն")).toBe(true);

    const ashot = runSearch({ ...newState(""), actor: ACTORS.indexOf("Աշոտ") });
    expect(ashot.length).toBeGreaterThan(0);
    expect(ashot.every((s) => s.actors.includes("Աշոտ"))).toBe(true);

    const short = runSearch({ ...newState(""), dur: 0 });
    expect(short.length).toBeGreaterThan(0);
    expect(short.every((s) => (s.durationSec ?? 0) < 120)).toBe(true);

    const combined = runSearch({
      ...newState(""), loc: LOCATIONS.indexOf("Տուն"), actor: ACTORS.indexOf("Մկո"), dur: 1,
    });
    expect(combined.length).toBeGreaterThan(0);
    expect(combined.length).toBeLessThan(all.length);
    expect(combined.every((s) =>
      s.location === "Տուն" && s.actors.includes("Մկո") &&
      (s.durationSec ?? 0) >= 120 && (s.durationSec ?? 0) <= 240,
    )).toBe(true);
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
    expect((rows[2][0] as { callback_data: string }).callback_data).toBe("b"); // browse
    expect((rows[2][1] as { callback_data: string }).callback_data).toBe("r");
    expect((rows[2][2] as { url: string }).url).toBe("https://karginhaghordum.am");
  });
  it("every example search actually returns results", () => {
    for (const e of EXAMPLES) expect(searchTop(e.q).length, e.q).toBeGreaterThan(0);
  });
  // Counting results is not enough: "Челентано" passed this for months while
  // returning unrelated sketches, because the query never reached the Latin song
  // credits and the old fuzzy pass matched Cyrillic dialogue instead. Each
  // example demonstrates a search TYPE, so check it demonstrates that type.
  it("every example returns a sketch that matches for the advertised reason", () => {
    const why: Record<string, (s: Sketch, q: string) => boolean> = {
      "💬": (s, q) => `${s.text} ${s.textCommon} ${s.transcript?.text ?? ""}`.toLowerCase().includes(q.toLowerCase()),
      "👤": (s, q) => s.actors.some((a) => a.toLowerCase().includes(q.toLowerCase())),
      "📍": (s, q) => s.location.toLowerCase().includes(q.toLowerCase()),
      "🎵": (s, q) => (s.songs ?? []).some((g) => `${g.artist} ${g.title}`.toLowerCase().includes(q.toLowerCase())),
      "🎬": (s, q) => JSON.stringify(s.visual ?? {}).toLowerCase().includes(q.toLowerCase()),
    };
    for (const e of EXAMPLES) {
      const top = searchTop(e.q).slice(0, 5);
      expect(top.some((s) => why[e.emoji](s, e.q)), `${e.emoji} ${e.q}`).toBe(true);
    }
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
