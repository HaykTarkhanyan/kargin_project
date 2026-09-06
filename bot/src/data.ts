/**
 * Loads the same sketches.json artifact the website bundles. Read via fs (not
 * an import) so the 2.6 MB JSON stays out of the JS bundle and the Docker
 * image can refresh it independently of the code. The path works from both
 * src/ (tsx) and dist/ (esbuild bundle) — each sits one level under bot/.
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { Sketch } from "../../web/lib/types";

const here = dirname(fileURLToPath(import.meta.url));
const DATA_PATH = join(here, "..", "..", "web", "public", "data", "sketches.json");

export const ALL: Sketch[] = JSON.parse(readFileSync(DATA_PATH, "utf8"));
if (!Array.isArray(ALL) || ALL.length === 0) {
  throw new Error(`sketches.json at ${DATA_PATH} is empty or not a list`);
}

const _byId = new Map(ALL.map((s) => [s.id, s]));
export const byId = (id: string): Sketch | undefined => _byId.get(id);

export function randomSketch(): Sketch {
  return ALL[Math.floor(Math.random() * ALL.length)];
}

/**
 * Facet values for the filter buttons, most frequent first. Callback data
 * carries INDEXES into these lists, not values — Armenian values eat the
 * 64-byte callback budget.
 */
function byFrequency(counts: Map<string, number>): string[] {
  return [...counts].sort((a, b) => b[1] - a[1]).map(([v]) => v);
}

export const LOCATIONS: string[] = byFrequency(ALL.reduce((m, s) => {
  m.set(s.location, (m.get(s.location) ?? 0) + 1);
  return m;
}, new Map<string, number>()));

// Top 7 = everyone with 22+ sketches; the tail (≤6 sketches each) isn't worth buttons.
export const ACTORS: string[] = byFrequency(ALL.reduce((m, s) => {
  for (const a of s.actors) m.set(a, (m.get(a) ?? 0) + 1);
  return m;
}, new Map<string, number>())).slice(0, 7);
