import Link from "next/link";
import type { Sketch } from "@/lib/types";
import type { Collection } from "@/lib/collections";

/** Thumbnails in the mosaic. */
const MOSAIC = 4;

/**
 * One collection as a tile: a mosaic of its most-viewed thumbnails, the name,
 * the description and how many sketches are in it.
 *
 * Members are passed in rather than looked up here, so the tile stays a pure
 * function of its props and the page decides the order.
 *
 * A collection with fewer than four members shows fewer thumbnails, and a single
 * member fills the whole box. Small collections are the point of curating by
 * hand, so they have to look deliberate rather than broken.
 */
export default function CollectionTile({
  collection, sketches,
}: {
  collection: Collection;
  sketches: Sketch[];
}) {
  const thumbs = sketches.slice(0, MOSAIC);
  const solo = thumbs.length === 1;

  return (
    <Link
      href={`/collections/${collection.slug}`}
      className="group flex h-full flex-col overflow-hidden rounded-xl k-border k-shadow transition hover:-translate-x-[3px] hover:-translate-y-[3px] hover:k-shadow-red bg-card"
    >
      <div className="grid aspect-video grid-cols-2 gap-0.5 border-b-2 border-ink bg-paper2">
        {thumbs.map((s) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            key={s.id}
            src={s.thumbnail}
            alt=""
            loading="lazy"
            className={`h-full w-full object-cover ${solo ? "col-span-2 row-span-2" : ""}`}
          />
        ))}
      </div>
      <div className="flex flex-1 flex-col p-4">
        <div className="font-display text-xl tracking-wide">{collection.name}</div>
        <div className="mt-1 text-sm leading-snug text-muted">{collection.description}</div>
        <div className="mt-auto pt-3 text-xs font-bold uppercase tracking-widest text-muted">
          {sketches.length} սքեթչ
        </div>
      </div>
    </Link>
  );
}
