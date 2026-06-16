import Fuse from "fuse.js";
import type { Sketch } from "./types";
import { romanize, cyrillize } from "./translit";

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

/**
 * Build a combined searchable string for a sketch that contains both the
 * original Armenian text and its romanized Latin equivalent. This lets a
 * Latin query (e.g. "tormuz") match Armenian dialogue (e.g. "տоռмuз")
 * without the caller needing to romanize the query.
 */
function buildSearchable(s: Sketch): string {
  const parts: string[] = [];
  for (const [field] of FIELDS) {
    const v = s[field];
    if (typeof v === "string" && v) {
      parts.push(v);
      // Append romanized (Latin) and cyrillized (Russian) forms so Latin/Cyrillic
      // queries match Armenian text without transliterating the query.
      const rom = romanize(v);
      if (rom !== v) parts.push(rom);
      const cyr = cyrillize(v);
      if (cyr !== v && cyr !== rom) parts.push(cyr);
    }
  }
  return parts.join(" ");
}

// Per-sketch combined searchable string (Armenian + Latin + Cyrillic), normalized
// and memoized so transliteration runs ONCE per sketch — not on every keystroke.
// Keyed by the sketch OBJECT (WeakMap) so it's safe even if two sketches share an id.
const _searchableCache = new WeakMap<Sketch, string>();
function getSearchable(s: Sketch): string {
  let c = _searchableCache.get(s);
  if (c === undefined) {
    c = normalize(buildSearchable(s));
    _searchableCache.set(s, c);
  }
  return c;
}

// ---------------------------------------------------------------------------
// Fuse.js word-level index
//
// We index one document per (sketchId, word) pair so that fuse can match
// individual words with tight thresholds rather than penalizing short queries
// against long field strings.
// ---------------------------------------------------------------------------

interface WordDoc { id: string; word: string }

let _fuseData: Sketch[] | null = null;
let _fuse: Fuse<WordDoc> | null = null;

function getFuse(data: Sketch[]): Fuse<WordDoc> {
  if (_fuse && _fuseData === data) return _fuse;
  _fuseData = data;

  const docs: WordDoc[] = [];
  for (const s of data) {
    const searchable = getSearchable(s);
    const words = searchable.split(/\s+/).filter((w) => w.length >= 2);
    for (const word of words) {
      docs.push({ id: s.id, word });
    }
  }

  _fuse = new Fuse(docs, {
    keys: ["word"],
    threshold: 0.35,     // 0.35 tolerates ~1-char typo in short words
    includeScore: true,
    minMatchCharLength: 2,
    ignoreLocation: true,
  });
  return _fuse;
}

export function searchSketches(query: string, data: Sketch[], filters: Filters, sort: SortKey = "views"): Sketch[] {
  const q = normalize(query);

  // --- Step 1: Exact (substring) matching over all FIELDS + romanized text ---
  const exactIds = new Set<string>();
  const scored: Array<{ s: Sketch; score: number }> = [];

  for (const s of data) {
    if (!passesFilters(s, filters)) continue;
    let score = 0;
    if (q) {
      // Check each weighted field for direct Armenian match.
      for (const [field, w] of FIELDS) {
        const v = s[field];
        if (typeof v === "string" && normalize(v).includes(q)) score += w;
      }
      // Also match if the query appears in the combined Latin/Cyrillic searchable string.
      if (score === 0 && getSearchable(s).includes(q)) score += 1;
      if (score === 0) continue;
    }
    exactIds.add(s.id);
    scored.push({ s, score });
  }

  // --- Step 2: Fuzzy matching via Fuse.js (only when a query exists) ---
  if (q) {
    const byId = new Map(data.map((s) => [s.id, s]));
    const fuse = getFuse(data);
    const fuseResults = fuse.search(q);

    // Collect the best score per sketch id from fuzzy word matches.
    const fuzzyBest = new Map<string, number>();
    for (const res of fuseResults) {
      const prev = fuzzyBest.get(res.item.id) ?? 1;
      const sc = res.score ?? 1;
      if (sc < prev) fuzzyBest.set(res.item.id, sc);
    }

    for (const [id, fuseScore] of fuzzyBest) {
      const s = byId.get(id);
      if (!s || !passesFilters(s, filters)) continue;
      if (exactIds.has(id)) continue; // already in exact results
      // Convert fuse score (0=perfect, 1=no match) to our score scale.
      // Fuzzy results are capped below 1 so exact matches always rank higher.
      const fuzzyScore = (1 - fuseScore) * 0.5;
      scored.push({ s, score: fuzzyScore });
    }
  }

  // --- Step 3: Sort ---
  if (sort === "random") {
    const arr = scored.map((x) => x.s);
    for (let i = arr.length - 1; i > 0; i--) {           // Fisher-Yates
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
