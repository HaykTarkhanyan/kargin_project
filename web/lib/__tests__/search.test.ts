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

// `songs` and `transcript` are objects, so the string-only FIELDS loop cannot
// reach them; both need their own branch in getIndex.
describe("non-string fields are searchable", () => {
  const song = { album: "", label: "", released: "", url: "", at: [30] };
  const data = [
    mk({ id: "s", title: "sketch 1", songs: [{ ...song, artist: "Michael Jackson", title: "Thriller" }] }),
    mk({ id: "c", title: "sketch 2", songs: [{ ...song, artist: "Adriano Celentano", title: "Susanna" }] }),
    mk({
      id: "t", title: "sketch 3",
      transcript: { text: "բարև ձեզ սիրելի հանդիսատես", source: "batch_reupload", events: 4, armenianChars: 24, novelty: 1 },
    }),
    mk({ id: "n", title: "sketch 4" }),
  ];

  it("finds a sketch by song title", () => {
    expect(searchSketches("Thriller", data, {}).map((s) => s.id)).toEqual(["s"]);
  });
  it("finds a sketch by artist", () => {
    expect(searchSketches("Celentano", data, {}).map((s) => s.id)).toEqual(["c"]);
  });
  it("finds a sketch whose only dialogue is a machine transcript", () => {
    expect(searchSketches("հանդիսատես", data, {}).map((s) => s.id)).toEqual(["t"]);
  });
  it("does not match sketches without songs or transcript", () => {
    expect(searchSketches("Thriller", data, {}).map((s) => s.id)).not.toContain("n");
  });
  it("ranks dialogue above a song hit for the same term", () => {
    const both = [
      mk({ id: "dialogue", text: "Սուսաննա ջան" }),
      mk({ id: "songonly", songs: [{ ...song, artist: "X", title: "Սուսաննա" }] }),
    ];
    expect(searchSketches("Սուսաննա", both, {})[0].id).toBe("dialogue");
  });

  const visual: NonNullable<Sketch["visual"]> = {
    locationFine: "village farm yard", synopsis: "A man argues with a stubborn donkey near a barn.",
    physicality: "physical", bestFrameTs: "01:10", confidence: "medium",
    animals: ["donkey"], keyProps: ["boombox"],
  };

  it("finds a sketch by what the visual annotation saw", () => {
    const data2 = [mk({ id: "v", visual }), mk({ id: "plain" })];
    expect(searchSketches("donkey", data2, {}).map((s) => s.id)).toEqual(["v"]);
    expect(searchSketches("boombox", data2, {}).map((s) => s.id)).toEqual(["v"]);
  });

  it("ranks a curated-text hit above a visual-only hit", () => {
    const data2 = [
      mk({ id: "visonly", visual: { ...visual, synopsis: "wedding at a barn" } }),
      mk({ id: "dialogue", text: "wedding խոսքը տեքստում է" }),
    ];
    expect(searchSketches("wedding", data2, {})[0].id).toBe("dialogue");
  });
});

// Real usage data (2026-09-11) showed visitors typing a line they remembered and
// getting nothing: 13 of ~56 distinct queries returned 0, almost all multi-word.
// The stored dialogue has different punctuation and filler, so the exact
// substring pass can never match a recalled phrase.
describe("multi-word queries match scattered words", () => {
  const line = mk({
    id: "line",
    text: "ինչ պտի ասես; էդ մեկը սովրել եմ ախպեր ջան",
  });
  const other = mk({ id: "other", text: "բոլորովին ուրիշ բան" });
  const onlyOne = mk({ id: "onlyone", text: "ասես մի բան" });
  const data = [line, other, onlyOne];

  it("finds a phrase split by punctuation the visitor did not type", () => {
    // "ասես էդ" spans the ';' — no contiguous substring, so this used to be 0.
    expect(searchSketches("ասես էդ մեկը", data, {}).map((s) => s.id)).toContain("line");
  });

  it("still finds it when a remembered word is wrong", () => {
    // 2 of 3 words present is enough; someone recalling a line misremembers one.
    expect(searchSketches("պտի ասես բան", data, {}).map((s) => s.id)).toContain("line");
  });

  it("does not return sketches matching only one word of several", () => {
    expect(searchSketches("ասես էդ մեկը", data, {}).map((s) => s.id)).not.toContain("other");
  });

  it("ranks a literal match above a scattered one", () => {
    const literal = mk({ id: "literal", text: "ասես էդ մեկը անփոփոխ" });
    const r = searchSketches("ասես էդ մեկը", [line, literal], {});
    expect(r[0].id).toBe("literal");
  });

  it("ranks words found close together above the same words scattered far apart", () => {
    const near = mk({ id: "near", text: "ասես էդ մեկը իրար կողքի" });
    const far = mk({
      id: "far",
      // same three words, pages apart — a coincidence, not the line
      text: `ասես ${"լցոն ".repeat(40)}էդ ${"լցոն ".repeat(40)}մեկը`,
    });
    const r = searchSketches("ասես էդ մեկը", [far, near], {});
    expect(r[0].id).toBe("near");
  });

  it("leaves single-word queries to the exact pass", () => {
    expect(searchSketches("ասես", data, {}).map((s) => s.id).sort()).toEqual(["line", "onlyone"]);
  });

  it("keeps matching while a word is still being typed", () => {
    expect(searchSketches("պտի աս", data, {}).map((s) => s.id)).toContain("line");
  });

  // A visitor after the role "Սամո" searched "սարո" — one letter out. Only a
  // near-spelling of the phrase's rarest word can reach that sketch, so fuzzy
  // feeds into the same scoring instead of sitting in a tier of its own.
  it("tolerates one misspelled word in a phrase", () => {
    const misspelled = [
      mk({ id: "samo", text: "սամո ջան արի ստեղ նստի", rolesNames: "Սամ/Սամո" }),
      mk({ id: "noise", text: "բոլորովին ուրիշ բան" }),
    ];
    const ids = searchSketches("սարո արի", misspelled, {}).map((s) => s.id);
    expect(ids).toContain("samo");
    expect(ids).not.toContain("noise");
  });

  it("ranks the correctly spelled word above the near-spelling", () => {
    const both = [
      mk({ id: "exact", text: "սարո ջան արի ստեղ" }),
      mk({ id: "near", text: "սամո ջան արի ստեղ" }),
    ];
    expect(searchSketches("սարո արի", both, {})[0].id).toBe("exact");
  });
});

describe("format", () => {
  it("formats views", () => { expect(formatViews(1358199)).toBe("1.4M"); expect(formatViews(813444)).toBe("813K"); });
  it("formats duration", () => { expect(formatDuration(242)).toBe("4:02"); });
});