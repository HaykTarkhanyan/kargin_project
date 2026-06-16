import type { Sketch } from "./types";

export interface Facets { location: Record<string, number>; actors: Record<string, number>; language: Record<string, number>; }

function tally(map: Record<string, number>, key: string) { if (key) map[key] = (map[key] ?? 0) + 1; }

export function facetCounts(data: Sketch[]): Facets {
  const f: Facets = { location: {}, actors: {}, language: {} };
  for (const s of data) {
    tally(f.location, s.location);
    s.actors.forEach((a) => tally(f.actors, a));
    s.languages.forEach((l) => tally(f.language, l));
  }
  return f;
}

export const sortedEntries = (m: Record<string, number>) =>
  Object.entries(m).sort((a, b) => b[1] - a[1]);