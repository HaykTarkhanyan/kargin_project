import type { Sketch } from "./types";
import sketches from "@/public/data/sketches.json";

export const ALL: Sketch[] = sketches as Sketch[];

// id -> sketch, built once. Used by the 702 static sketch pages at build time.
const _byId = new Map<string, Sketch>(ALL.map((s) => [s.id, s]));
export const byId = (id: string): Sketch | undefined => _byId.get(id);
