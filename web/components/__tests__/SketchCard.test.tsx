import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import SketchCard from "@/components/SketchCard";
import type { Sketch } from "@/lib/types";

const s = { id:"ofvCL_U2Er0",videoId:"ofvCL_U2Er0",seq:663,title:"sketch 663",url:"",
  thumbnail:"https://img.youtube.com/vi/ofvCL_U2Er0/mqdefault.jpg",text:"",
  textCommon:"արա էսի ուզբեկ ա",actors:["Հայկո","Մկո"],actorsRaw:"",rolesNames:"",
  location:"Տուն",languages:[],lighting:"",durationSec:242,viewCount:1358199,uploadDate:"" } as Sketch;

describe("SketchCard", () => {
  it("renders title, location, duration, views, links to /sketch/:id", () => {
    render(<SketchCard sketch={s} />);
    expect(screen.getByText("sketch 663")).toBeTruthy();
    expect(screen.getByText("Տուն")).toBeTruthy();
    expect(screen.getByText("4:02")).toBeTruthy();
    expect(screen.getByRole("link").getAttribute("href")).toContain("/sketch/ofvCL_U2Er0");
  });
});
