import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import SongList from "@/components/SongList";
import type { Song } from "@/lib/types";

const song: Song = {
  artist: "Henry Mancini", title: "The Pink Panther Theme",
  album: "", label: "RCA Records Label", released: "1982",
  url: "https://www.shazam.com/track/1", at: [90, 150],
};

describe("SongList", () => {
  it("renders nothing when there are no songs", () => {
    const { container } = render(<SongList songs={[]} watchUrl="https://youtu.be/x" />);
    expect(container.firstChild).toBeNull();
  });

  it("shows title, artist and label/year", () => {
    render(<SongList songs={[song]} watchUrl="https://youtu.be/x" />);
    expect(screen.getByText("The Pink Panther Theme")).toBeTruthy();
    expect(screen.getByText("Henry Mancini")).toBeTruthy();
    expect(screen.getByText("RCA Records Label · 1982")).toBeTruthy();
  });

  it("deep-links each timestamp to YouTube at that second", () => {
    render(<SongList songs={[song]} watchUrl="https://youtu.be/abc" />);
    const links = screen.getAllByRole("link").filter((a) => a.textContent?.includes("▶"));
    expect(links).toHaveLength(2);
    expect(links[0].getAttribute("href")).toBe("https://youtu.be/abc?t=90");
    expect(links[1].getAttribute("href")).toBe("https://youtu.be/abc?t=150");
    expect(links[0].textContent).toContain("1:30");
  });

  it("omits the label line when neither label nor year is known", () => {
    const bare = { ...song, label: "", released: "" };
    render(<SongList songs={[bare]} watchUrl="https://youtu.be/x" />);
    expect(screen.queryByText("·")).toBeNull();
  });
});
