import type { Metadata } from "next";
import Link from "next/link";
import { allCollections, sketchesFor } from "@/lib/collections";
import CollectionTile from "@/components/CollectionTile";

export const metadata: Metadata = {
  title: "Հավաքածուներ — Կարգին Արխիվ",
  description: "Ձեռքով հավաքված սքեթչեր՝ ըստ իրավիճակի։",
};

// Server component: the whole list is computed at build time.
const collections = allCollections();
const total = collections.reduce((sum, c) => sum + c.sketchIds.length, 0);

export default function CollectionsPage() {
  return (
    <div className="px-4 py-8 sm:px-8">
      <div className="mb-6">
        <Link
          href="/"
          className="mb-3 inline-block text-xs font-bold uppercase tracking-widest text-muted hover:text-ink"
        >
          ← Որոնել
        </Link>
        <h1 className="font-display text-5xl sm:text-6xl">ՀԱՎԱՔԱԾՈՒՆԵՐ</h1>
        <p className="mt-3 max-w-2xl text-sm text-muted">
          Ձեռքով հավաքված խմբեր՝ ըստ իրավիճակի, ոչ ըստ դերասանի կամ վայրի։{" "}
          {collections.length} հավաքածու, {total} սքեթչ։
        </p>
      </div>
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
        {collections.map((c) => (
          <CollectionTile key={c.slug} collection={c} sketches={sketchesFor(c.slug)} />
        ))}
      </div>
    </div>
  );
}
