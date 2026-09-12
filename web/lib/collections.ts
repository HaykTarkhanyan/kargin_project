import type { Sketch } from "./types";
import { byId } from "./data";
import raw from "@/public/data/collections.json";

/**
 * Hand-curated groups of sketches: "they play cards", "at the doctor".
 * Built from kargin_eng.csv plus data/collections.csv by
 * scripts/build_collections.py (DECISIONS.md #17).
 *
 * Server components only. Membership deliberately does NOT live on the Sketch
 * type: everything a sketch carries ships inside the home page's JavaScript,
 * because SearchExperience is a client component that imports the whole payload.
 * Nothing the Telegram bot imports may reach this module either -- bot/Dockerfile
 * copies web/lib and sketches.json, not this file's JSON.
 */
export interface Collection {
  slug: string;
  name: string;
  description: string;
  sketchIds: string[];
}

const COLLECTIONS: Collection[] = raw as Collection[];

export const allCollections = (): Collection[] => COLLECTIONS;

export const collectionBySlug = (slug: string): Collection | undefined =>
  COLLECTIONS.find((c) => c.slug === slug);

/**
 * Members as sketches, most viewed first. Sorting here rather than in the build
 * keeps collections.json independent of youtube_metadata.csv.
 *
 * Throws on an id that is not in the payload: the build validates membership
 * against kargin_eng.csv, so a mismatch here means the two files disagree, and
 * failing the build is better than a collection that quietly lost a sketch.
 */
export function sketchesFor(slug: string): Sketch[] {
  const collection = collectionBySlug(slug);
  if (!collection) return [];
  return collection.sketchIds
    .map((id) => {
      const sketch = byId(id);
      if (!sketch) throw new Error(`collections: ${slug} lists ${id}, absent from sketches.json`);
      return sketch;
    })
    .sort((a, b) => (b.viewCount ?? 0) - (a.viewCount ?? 0));
}

/** Which collections a sketch is in, for the chip on its own page. */
export const collectionsForSketch = (id: string): Collection[] =>
  COLLECTIONS.filter((c) => c.sketchIds.includes(id));
