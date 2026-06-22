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
});
