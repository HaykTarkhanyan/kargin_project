import type { Sketch } from "./types";

export interface Filters {
  location?: string[]; actors?: string[]; language?: string[]; duration?: "<2" | "2-4" | "4+";
}
export type SortKey = "views" | "newest" | "random";

export function normalize(s: string): string {
  return s.toLowerCase().normalize("NFC").replace(/\s+/g, " ").trim();
}

// Field weights: catchphrase + title rank highest, then dialogue, then people/place.
const FIELDS: Array<[keyof Sketch, number]> = [
  ["textCommon", 5], ["title", 4], ["text", 3], ["actorsRaw", 2], ["rolesNames", 1], ["location", 1],
];

function durationOk(sec: number | null, bucket?: Filters["duration"]): boolean {
  if (!bucket || sec == null) return !bucket;
  if (bucket === "<2") return sec < 120;
  if (bucket === "2-4") return sec >= 120 && sec <= 240;
  return sec > 240;
}

function passesFilters(s: Sketch, f: Filters): boolean {
  if (f.location?.length && !f.location.includes(s.location)) return false;
  if (f.actors?.length && !f.actors.some((a) => s.actors.includes(a))) return false;
  if (f.language?.length && !f.language.some((l) => s.languages.includes(l))) return false;
  if (f.duration && !durationOk(s.durationSec, f.duration)) return false;
  return true;
}

export function searchSketches(query: string, data: Sketch[], filters: Filters, sort: SortKey = "views"): Sketch[] {
  const q = normalize(query);
  const scored: Array<{ s: Sketch; score: number }> = [];
  for (const s of data) {
    if (!passesFilters(s, filters)) continue;
    let score = 0;
    if (q) {
      for (const [field, w] of FIELDS) {
        const v = s[field];
        if (typeof v === "string" && normalize(v).includes(q)) score += w;
      }
      if (score === 0) continue; // query given but no field matched → drop
    }
    scored.push({ s, score });
  }
  if (sort === "random") {
    const arr = scored.map((x) => x.s);
    for (let i = arr.length - 1; i > 0; i--) {           // Fisher-Yates — actually shuffle
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }
  scored.sort((a, b) => {
    if (q && b.score !== a.score) return b.score - a.score;
    if (sort === "newest") return (b.s.uploadDate).localeCompare(a.s.uploadDate);
    return (b.s.viewCount ?? 0) - (a.s.viewCount ?? 0);
  });
  return scored.map((x) => x.s);
}