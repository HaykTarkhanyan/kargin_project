import Link from "next/link";
import { allCollections, sketchesFor } from "@/lib/collections";
import CollectionTile from "./CollectionTile";

/** Collections shown on the home page before the full list is worth a click. */
const STRIP_MAX = 3;

/**
 * The home page teaser. Rendered on the server by app/page.tsx and handed to
 * SearchExperience as a prop, so collections.json never reaches the browser.
 *
 * It lands inside SearchExperience's Suspense boundary, which means it paints
 * with the hero and the results rather than in the exported HTML. That is
 * already true of everything below the header on this page; /collections is the
 * statically rendered surface for this content.
 */
export default function CollectionStrip() {
  const collections = allCollections().slice(0, STRIP_MAX);
  if (collections.length === 0) return null;

  return (
    <section className="border-b-2 border-ink px-4 py-6 sm:px-8">
      <div className="mb-4 flex items-baseline justify-between gap-3">
        <h2 className="font-display text-xl tracking-wide sm:text-2xl">ՀԱՎԱՔԱԾՈՒՆԵՐ</h2>
        <Link
          href="/collections"
          className="whitespace-nowrap text-xs font-bold uppercase tracking-widest text-muted hover:text-ink"
        >
          տեսնել բոլորը →
        </Link>
      </div>
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
        {collections.map((c) => (
          <CollectionTile key={c.slug} collection={c} sketches={sketchesFor(c.slug)} />
        ))}
      </div>
    </section>
  );
}
