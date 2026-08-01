import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import SketchCard from "@/components/SketchCard";
import type { Sketch } from "@/lib/types";

const s = { id:"ofvCL_U2Er0",videoId:"ofvCL_U2Er0",seq:663,title:"sketch 663",url:"",
  thumbnail:"https://img.youtube.com/vi/ofvCL_U2Er0/mqdefault.jpg",text:"",
  textCommon:"արա էսի ուզբեկ ա",actors:["Հայկո","Մկո"],actorsRaw:"",rolesNames:"",
  location:"Տուն",languages:[],lighting:"",durationSec:242,viewCount:1358199,uploadDate:"" } as Sketch;

const withText = { ...s, text: "բարև ձեզ; ոնց ես ախպեր; վերջին տողը" } as Sketch;

describe("SketchCard", () => {
  it("renders title, location, duration, views, links to /sketch/:id", () => {
    render(<SketchCard sketch={s} />);
    expect(screen.getByText("sketch 663")).toBeTruthy();
    expect(screen.getByText("Տուն")).toBeTruthy();
    expect(screen.getByText("4:02")).toBeTruthy();
    expect(screen.getByRole("link").getAttribute("href")).toContain("/sketch/ofvCL_U2Er0");
  });

  it("shows the full dialogue, not just a snippet", () => {
    render(<SketchCard sketch={withText} />);
    expect(screen.getByText("բարև ձեզ")).toBeTruthy();
    expect(screen.getByText("ոնց ես ախպեր")).toBeTruthy();
    expect(screen.getByText("վերջին տողը")).toBeTruthy();
  });

  it("marks the matching text and reports how many lines matched", () => {
    const { container } = render(<SketchCard sketch={withText} query="ախպեր" />);
    const marks = container.querySelectorAll("mark");
    expect(marks).toHaveLength(1);
    expect(marks[0].textContent).toBe("ախպեր");
    expect(screen.getByText("1 համընկնում")).toBeTruthy();
  });

  it("adds no marks and no match count without a query", () => {
    const { container } = render(<SketchCard sketch={withText} />);
    expect(container.querySelectorAll("mark")).toHaveLength(0);
    expect(screen.queryByText(/համընկնում/)).toBeNull();
  });

  it("badges how many songs were identified, and none when there are none", () => {
    const withSongs = { ...s, songs: [
      { artist: "ABBA", title: "Dancing Queen", album: "", label: "Polar", released: "1976", url: "", at: [150] },
      { artist: "Eruption", title: "One Way Ticket", album: "", label: "", released: "", url: "", at: [0, 30] },
    ] } as Sketch;
    render(<SketchCard sketch={withSongs} />);
    expect(screen.getByText("🎵 2")).toBeTruthy();

    render(<SketchCard sketch={s} />);
    expect(screen.queryAllByText(/🎵/)).toHaveLength(1); // only the one above
  });

  it("still renders sketches that have no dialogue", () => {
    const { container } = render(<SketchCard sketch={s} query="ուզբեկ" />);
    expect(screen.getByText("sketch 663")).toBeTruthy();
    expect(container.querySelectorAll("mark")).toHaveLength(1); // matches the catchphrase
  });
});
