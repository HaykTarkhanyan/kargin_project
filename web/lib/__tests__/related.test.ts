import { describe, it, expect } from "vitest";
import { related } from "@/lib/related";
import type { Sketch } from "@/lib/types";

const mk = (p: Partial<Sketch>): Sketch => ({ id:"x",videoId:"x",seq:1,title:"",url:"",thumbnail:"",
  text:"",textCommon:"",actors:[],actorsRaw:"",rolesNames:"",location:"Այլ",languages:[],
  lighting:"",durationSec:120,viewCount:0,uploadDate:"",...p });

describe("related", () => {
  // duo is everywhere; a shared RARE guest should beat a shared ubiquitous lead
  const target = mk({ id:"t", actors:["Հայկո","Մկո","Աշոտ"] });
  const all = [
    target,
    mk({ id:"rareGuest", actors:["Աշոտ"], viewCount: 1 }),          // shares rare Աշոտ
    mk({ id:"justDuo", actors:["Հայկո","Մկո"], viewCount: 9_000_000 }), // shares ubiquitous duo, huge views
    ...Array.from({length:20},(_,i)=>mk({id:"duo"+i,actors:["Հայկո","Մկո"],viewCount:1000})),
  ];
  it("ranks a shared rare guest above a shared ubiquitous lead", () => {
    const r = related(target, all, 6).map(s=>s.id);
    expect(r.indexOf("rareGuest")).toBeLessThan(r.indexOf("justDuo"));
  });
  it("excludes self and never returns more than limit", () => {
    const r = related(target, all, 6);
    expect(r.find(s=>s.id==="t")).toBeUndefined();
    expect(r.length).toBe(6);
  });
  it("falls back to popular when no overlap, never empty", () => {
    const lonely = mk({ id:"lonely", actors:[], location:"Այլ" });
    const r = related(lonely, [lonely, ...all], 6);
    expect(r.length).toBe(6);
  });

  // Semantic neighbours (embeddings) outrank actor overlap: they match on what
  // the sketch is about, which is the whole point of shipping them.
  it("puts semantic neighbours first, in their given order", () => {
    const t = mk({ id:"t2", actors:["Հայկո","Մկո"], similar:[
      { id:"sem1", score:0.88 }, { id:"sem2", score:0.79 },
    ]});
    const pool = [t, mk({id:"sem1",actors:[]}), mk({id:"sem2",actors:[]}), ...all];
    const r = related(t, pool, 6).map(s=>s.id);
    expect(r.slice(0,2)).toEqual(["sem1","sem2"]);
    expect(r.length).toBe(6);
  });

  it("fills the remainder from actor overlap without repeating a semantic hit", () => {
    const t = mk({ id:"t3", actors:["Աշոտ"], similar:[{ id:"rareGuest", score:0.9 }] });
    const r = related(t, [t, ...all], 6).map(s=>s.id);
    expect(r[0]).toBe("rareGuest");
    expect(r.filter(id=>id==="rareGuest").length).toBe(1);   // not duplicated by the actor pass
    expect(r.length).toBe(6);
  });

  it("ignores similar ids that are not in the dataset", () => {
    const t = mk({ id:"t4", actors:["Հայկո"], similar:[{ id:"ghost", score:0.95 }] });
    const r = related(t, [t, ...all], 6).map(s=>s.id);
    expect(r).not.toContain("ghost");
    expect(r.length).toBe(6);
  });

  it("never returns the target even if it appears in its own similar list", () => {
    const t = mk({ id:"t5", actors:[], similar:[{ id:"t5", score:1 }] });
    const r = related(t, [t, ...all], 6);
    expect(r.find(s=>s.id==="t5")).toBeUndefined();
  });
});
