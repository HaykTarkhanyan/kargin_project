import type { Sketch } from "./types";
import { ALL } from "./data";

export function getActorNames(): string[] {
  return [...new Set(ALL.flatMap((s) => s.actors))].sort();
}

export function getSketchesForActor(name: string): Sketch[] {
  return ALL.filter((s) => s.actors.includes(name));
}

/** Returns co-star counts for an actor, sorted descending. */
export function getCoStars(name: string, sketches: Sketch[]): { name: string; count: number }[] {
  const counts: Record<string, number> = {};
  for (const s of sketches) {
    for (const a of s.actors) {
      if (a !== name) {
        counts[a] = (counts[a] ?? 0) + 1;
      }
    }
  }
  return Object.entries(counts)
    .map(([n, count]) => ({ name: n, count }))
    .sort((a, b) => b.count - a.count);
}
