import type { Stats } from "./stats-types";
import raw from "@/public/data/stats.json";

export const STATS = raw as Stats;
if (!STATS.totals || !STATS.coOccurrence) throw new Error("stats.json shape mismatch — rebuild it");
