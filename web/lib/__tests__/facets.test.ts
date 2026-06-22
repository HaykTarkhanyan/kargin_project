import { describe, it, expect } from "vitest";
import { facetCounts } from "@/lib/facets";
import type { Sketch } from "@/lib/types";

const mk = (p: Partial<Sketch>): Sketch => ({ id:"x",videoId:"x",seq:null,title:"",url:"",thumbnail:"",
  text:"",textCommon:"",actors:[],actorsRaw:"",rolesNames:"",location:"Այլ",languages:[],
  lighting:"",durationSec:120,viewCount:0,uploadDate:"",...p });

describe("facetCounts", () => {
  it("counts locations and actors over the dataset", () => {
    const data = [
      mk({ location: "Տուն", actors: ["Հայկո", "Մկո"] }),
      mk({ location: "Տուն", actors: ["Հայկո"] }),
      mk({ location: "Խանութ", actors: [] }),
    ];
    const f = facetCounts(data);
    expect(f.location["Տուն"]).toBe(2);
    expect(f.location["Խանութ"]).toBe(1);
    expect(f.actors["Հայկո"]).toBe(2);
    expect(f.actors["Մկո"]).toBe(1);
  });
});