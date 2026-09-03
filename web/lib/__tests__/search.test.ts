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

describe("format", () => {
  it("formats views", () => { expect(formatViews(1358199)).toBe("1.4M"); expect(formatViews(813444)).toBe("813K"); });
  it("formats duration", () => { expect(formatDuration(242)).toBe("4:02"); });
});