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
