import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import CollectionTile from "@/components/CollectionTile";
import type { Collection } from "@/lib/collections";
import type { Sketch } from "@/lib/types";

const collection: Collection = {
  slug: "cards",
  name: "Թուղթ խաղում են",
  description: "Սեղանի շուրջ՝ թղթախաղ։",
  sketchIds: [],
};

const sketch = (id: string): Sketch =>
  ({ id, title: `sketch ${id}`, thumbnail: `https://i.ytimg.com/vi/${id}/hq.jpg`,
     viewCount: 1, actors: [], location: "Տուն" } as unknown as Sketch);

const many = (n: number) => Array.from({ length: n }, (_, i) => sketch(`id${i}`));

describe("CollectionTile", () => {
  it("shows the name, the description, the count and links to the collection", () => {
    const { container } = render(<CollectionTile collection={collection} sketches={many(3)} />);
    expect(screen.getByText(collection.name)).toBeTruthy();
    expect(screen.getByText(collection.description)).toBeTruthy();
    expect(screen.getByText("3 սքեթչ")).toBeTruthy();
    // No trailing slash, like every other internal link here; next.config's
    // trailingSlash setting canonicalises the exported path.
    expect(container.querySelector("a")?.getAttribute("href")).toBe("/collections/cards");
  });

  it("caps the mosaic at four thumbnails but still counts them all", () => {
    const { container } = render(<CollectionTile collection={collection} sketches={many(5)} />);
    expect(container.querySelectorAll("img")).toHaveLength(4);
    expect(screen.getByText("5 սքեթչ")).toBeTruthy();
  });

  it("shows fewer thumbnails for a small collection", () => {
    const { container } = render(<CollectionTile collection={collection} sketches={many(3)} />);
    expect(container.querySelectorAll("img")).toHaveLength(3);
  });

  // A one-sketch collection should look deliberate, not like a broken grid.
  it("lets a single thumbnail fill the mosaic", () => {
    const { container } = render(<CollectionTile collection={collection} sketches={many(1)} />);
    const imgs = container.querySelectorAll("img");
    expect(imgs).toHaveLength(1);
    expect(imgs[0].className).toContain("col-span-2");
  });

  it("does not stretch a thumbnail when there are several", () => {
    const { container } = render(<CollectionTile collection={collection} sketches={many(2)} />);
    expect(container.querySelectorAll("img")[0].className).not.toContain("col-span-2");
  });
});
