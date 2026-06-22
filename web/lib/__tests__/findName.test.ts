import { describe, it, expect } from "vitest";
import { findByName } from "@/lib/findName";
import type { Sketch } from "@/lib/types";

const mk = (p: Partial<Sketch>): Sketch => ({ id:"x",videoId:"x",seq:1,title:"",url:"",thumbnail:"",
  text:"",textCommon:"",actors:[],actorsRaw:"",rolesNames:"",location:"Այլ",languages:[],
  lighting:"",durationSec:120,viewCount:0,uploadDate:"",...p });

describe("findByName", () => {
  const all = [
    mk({ id:"acts", actors:["Հասմիկ"] }),
    mk({ id:"mention", text:"բարև Անիին ասա" }),
    mk({ id:"falsepos", text:"ընկավ պատուհանից" }),  // contains 'անի' but must NOT match Անի
  ];
  it("classifies an actor match", () => {
    const r = findByName("Հասմիկ", all);
    expect(r.find(x=>x.sketch.id==="acts")?.kind).toBe("actor");
  });
  it("classifies a dialogue mention and ignores mid-word false positives", () => {
    const r = findByName("Անի", all);
    const ids = r.map(x=>x.sketch.id);
    expect(ids).toContain("mention");
    expect(ids).not.toContain("falsepos");
    expect(r.find(x=>x.sketch.id==="mention")?.kind).toBe("mention");
  });
});
