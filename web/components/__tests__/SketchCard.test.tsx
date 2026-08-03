import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import SketchCard from "@/components/SketchCard";
import type { Sketch } from "@/lib/types";

const s = { id:"ofvCL_U2Er0",videoId:"ofvCL_U2Er0",seq:663,title:"sketch 663",url:"",
  thumbnail:"https://img.youtube.com/vi/ofvCL_U2Er0/mqdefault.jpg",text:"",
  textCommon:"արա էսի ուզբեկ ա",actors:["Հայկո","Մկո"],actorsRaw:"",rolesNames:"",
  location:"Տուն",languages:[],lighting:"",durationSec:242,viewCount:1358199,uploadDate:"" } as Sketch;

const withText = { ...s, text: "բարև ձեզ; ոնց ես ախպեր; վերջին տողը" } as Sketch;

const transcript = {
  text: "ասաց գնանք տուն\nքույրս սպասում է դռան մոտ",
  source: "batch_reupload", events: 2, armenianChars: 40, novelty: 1,
} as const;

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

  // Search indexes the transcript as well as the curated text, so a card can be
  // returned for a word that appears only in the transcript. 68 sketches carry
  // both; without the fallback those render "0 matches" and nothing highlighted.
  it("falls back to the transcript when the query matched only there", () => {
    const both = { ...withText, transcript } as Sketch;
    const { container } = render(<SketchCard sketch={both} query="քույրս" />);
    expect(container.querySelector("mark")?.textContent).toBe("քույրս");
    expect(screen.getByText("1 համընկնում")).toBeTruthy();
    expect(screen.getByText(/ավտոմատ/)).toBeTruthy();
  });

  it("keeps curated dialogue when the query matches it, even if a transcript exists", () => {
    const both = { ...withText, transcript } as Sketch;
    // The matched line is split around <mark>, so assert on the mark rather
    // than the whole line.
    const { container } = render(<SketchCard sketch={both} query="ախպեր" />);
    expect(container.querySelector("mark")?.textContent).toBe("ախպեր");
    expect(screen.getByText("բարև ձեզ")).toBeTruthy();      // unmatched curated line still shown
    expect(screen.queryByText(/ավտոմատ/)).toBeNull();
  });

  it("prefers curated dialogue over a transcript when there is no query", () => {
    const both = { ...withText, transcript } as Sketch;
    render(<SketchCard sketch={both} />);
    expect(screen.getByText("բարև ձեզ")).toBeTruthy();
    expect(screen.queryByText(/ավտոմատ/)).toBeNull();
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
