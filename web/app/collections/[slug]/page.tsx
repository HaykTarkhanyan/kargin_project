import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { allCollections, collectionBySlug, sketchesFor } from "@/lib/collections";
import { formatViews } from "@/lib/format";
import SketchGrid from "@/components/SketchGrid";

export function generateStaticParams() {
  // Slugs are ascii by build-time validation, so no encoding dance here -- unlike
  // the actor pages, which carry raw Armenian in the path.
  return allCollections().map((c) => ({ slug: c.slug }));
}

export async function generateMetadata(
  { params }: { params: Promise<{ slug: string }> },
): Promise<Metadata> {
  const { slug } = await params;
  const collection = collectionBySlug(slug);
  if (!collection) return {};
  return { title: `${collection.name} — Կարգին Արխիվ`, description: collection.description };
}

export default async function CollectionPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const collection = collectionBySlug(slug);
  if (!collection) notFound();

  // No 48-card cap like the actor pages: collections are small by construction,
  // and this page is the destination rather than a taster for search.
  const sketches = sketchesFor(slug);
  const totalViews = sketches.reduce((sum, s) => sum + (s.viewCount ?? 0), 0);

  return (
    <div className="px-4 py-8 sm:px-8">
      <div className="mb-6">
        <Link
          href="/collections"
          className="mb-3 inline-block text-xs font-bold uppercase tracking-widest text-muted hover:text-ink"
        >
          ← Հավաքածուներ
        </Link>
        <h1 className="font-display text-5xl sm:text-6xl">{collection.name}</h1>
        <p className="mt-3 max-w-2xl text-sm text-muted">{collection.description}</p>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 sm:max-w-md">
        <div className="k-border k-shadow rounded-lg bg-card p-4">
          <div className="font-display text-3xl text-kred">{sketches.length}</div>
          <div className="text-[10px] font-bold uppercase tracking-widest text-muted">սքեթչ</div>
        </div>
        <div className="k-border k-shadow rounded-lg bg-card p-4">
          <div className="font-display text-3xl text-kblue">{formatViews(totalViews)}</div>
          <div className="text-[10px] font-bold uppercase tracking-widest text-muted">ընդհանուր դիտում</div>
        </div>
      </div>

      <SketchGrid items={sketches} />
    </div>
  );
}
