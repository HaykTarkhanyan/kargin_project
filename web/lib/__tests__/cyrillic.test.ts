import { describe, it, expect } from "vitest";
import { cyrillize } from "@/lib/translit";
import { searchSketches } from "@/lib/search";
import type { Sketch } from "@/lib/types";

const mk = (p: Partial<Sketch>): Sketch => ({ id:"x",videoId:"x",seq:1,title:"",url:"",thumbnail:"",
  text:"",lines:[],textCommon:"",actors:[],actorsRaw:"",rolesNames:"",location:"Այլ",languages:[],
  lighting:"",durationSec:120,viewCount:0,uploadDate:"",segments:[],...p });

describe("cyrillize", () => {
  it("maps Armenian to Russian-Cyrillic phonetically", () => {
    expect(cyrillize("տոռմուզ")).toBe("тормуз");   // ту-digraph ու → у
    expect(cyrillize("Հայկո")).toBe("гайко");
  });
  it("passes non-Armenian through lowercased", () => {
    expect(cyrillize("ABC 123")).toBe("abc 123");
  });
});

describe("Cyrillic search (like romanized)", () => {
  const data = [
    mk({ id: "a", text: "Հոպ ընգեր ջան, տոռմուզ հըլը" }),
    mk({ id: "b", textCommon: "լվացքի փոշի" }),
  ];
  it("finds Armenian dialogue from a Cyrillic query", () => {
    expect(searchSketches("тормуз", data, {}).map((s) => s.id)).toContain("a");
  });
  it("still finds from a Latin query (romanized path intact)", () => {
    expect(searchSketches("tormuz", data, {}).map((s) => s.id)).toContain("a");
  });
  it("Armenian query still works", () => {
    expect(searchSketches("տոռմուզ", data, {}).map((s) => s.id)).toContain("a");
  });
});
