import type { Sketch } from "./types";
import sketches from "@/public/data/sketches.json";

export const ALL: Sketch[] = sketches as Sketch[];
export const byId = (id: string): Sketch | undefined => ALL.find((s) => s.id === id);
