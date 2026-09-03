import Fuse from "fuse.js";
import type { Sketch } from "./types";
import { romanize, cyrillize } from "./translit";
import { normalize } from "./normalize";

export interface Filters {
  location?: string[]; actors?: string[]; language?: string[]; duration?: "<2" | "2-4" | "4+";
}
export type SortKey = "views" | "newest" | "random";

// Re-exported for existing callers; the definition moved to ./normalize so that
// importing it does not pull Fuse.js in with it.
export { normalize };

// Field weights: catchphrase + title rank highest, then dialogue, then people/place.
const FIELDS: Array<[keyof Sketch, number]> = [
  ["textCommon", 5], ["title", 4], ["text", 3], ["actorsRaw", 2], ["rolesNames", 1], ["location", 1],
];

// Below curated dialogue (3): a transcript is machine output, so a hit in it is
// weaker evidence than a hit in text a person wrote. Indexed separately because
// `transcript` is an object and the FIELDS loop only walks string properties.
const TRANSCRIPT_WEIGHT = 2;

// Songs sit alongside actors at 2: naming the music is a real way to find a
// sketch ("Thriller", "Челентано"), but it describes the soundtrack rather than
// what the sketch is about, so it should not outrank the dialogue.
const SONG_WEIGHT = 2;

// Visual annotations are machine descriptions in English — weight 1, below
// everything a person wrote. What they buy: "cow", "lada", "casino", "wedding"
// find sketches whose dialogue never says those words.
const VISUAL_WEIGHT = 1;

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

// ---------------------------------------------------------------------------
// Per-sketch normalized index, computed ONCE (memoized by sketch object).
//   combined = normalized Armenian + romanized + cyrillized text (one .includes target)
//   fields   = [normalizedFieldValue, weight] for weighting matches
// This keeps each keystroke to cheap `.includes` on cached strings — no per-key NFC.
// ---------------------------------------------------------------------------
interface SketchIndex { combined: string; fields: Array<[string, number]> }
const _indexCache = new WeakMap<Sketch, SketchIndex>();

function getIndex(s: Sketch): SketchIndex {
  let idx = _indexCache.get(s);
  if (idx) return idx;
  const fields: Array<[string, number]> = [];
  const parts: string[] = [];
  const add = (v: string, w: number) => {
    fields.push([normalize(v), w]);
    parts.push(v);
    const rom = romanize(v); if (rom !== v) parts.push(rom);          // Latin queries
    const cyr = cyrillize(v); if (cyr !== v && cyr !== rom) parts.push(cyr); // Cyrillic queries
  };
  for (const [field, w] of FIELDS) {
    const v = s[field];
    if (typeof v === "string" && v) add(v, w);
  }
  // For 95 sketches this is the only dialogue there is; without it they match
  // nothing but their own title.
  if (s.transcript?.text) add(s.transcript.text, TRANSCRIPT_WEIGHT);
  // Artist and title only. Album and label are catalogue detail nobody searches
  // by, and including them would dilute the index with reissue names.
  if (s.songs?.length) {
    add(s.songs.map((x) => `${x.artist} ${x.title}`).join(" "), SONG_WEIGHT);
  }
  if (s.visual) {
    add(
      [s.visual.synopsis, s.visual.locationFine,
       ...(s.visual.characterTypes ?? []), ...(s.visual.keyProps ?? []),
       ...(s.visual.animals ?? []), ...(s.visual.vehicles ?? [])].join(" "),
      VISUAL_WEIGHT,
    );
  }
  idx = { combined: normalize(parts.join(" ")), fields };
  _indexCache.set(s, idx);
  return idx;
}

// ---------------------------------------------------------------------------
// Fuzzy index — Fuse over UNIQUE words (a few thousand), not one doc per
// (sketch, word) (~100k+). A word maps back to the sketches that contain it.
// Built once per dataset; fuzzy is only consulted when exact results are sparse.
// ---------------------------------------------------------------------------
let _fuseData: Sketch[] | null = null;
let _fuse: Fuse<{ word: string }> | null = null;
let _wordToIds: Map<string, Set<string>> = new Map();
let _byId: Map<string, Sketch> = new Map();

function buildFuzzy(data: Sketch[]): void {
  if (_fuse && _fuseData === data) return;
  _fuseData = data;
  _wordToIds = new Map();
  _byId = new Map();
  for (const s of data) {
    _byId.set(s.id, s);
    for (const word of getIndex(s).combined.split(" ")) {
      if (word.length < 2) continue;
      let set = _wordToIds.get(word);
      if (!set) { set = new Set(); _wordToIds.set(word, set); }
      set.add(s.id);
    }
  }
  _fuse = new Fuse([..._wordToIds.keys()].map((word) => ({ word })), {
    keys: ["word"], threshold: 0.35, includeScore: true, minMatchCharLength: 2, ignoreLocation: true,
  });
}

const FUZZY_WHEN_FEWER_THAN = 12; // only fuzzy-search if exact found < this

export function searchSketches(query: string, data: Sketch[], filters: Filters, sort: SortKey = "views"): Sketch[] {
  const q = normalize(query);

  // --- Step 1: exact (substring) match over cached normalized text ---
  const exactIds = new Set<string>();
  const scored: Array<{ s: Sketch; score: number }> = [];
  for (const s of data) {
    if (!passesFilters(s, filters)) continue;
    if (!q) { scored.push({ s, score: 0 }); continue; }
    const idx = getIndex(s);
    if (!idx.combined.includes(q)) continue;            // cheap: cached normalized string
    let score = 0;
    for (const [val, w] of idx.fields) if (val.includes(q)) score += w;
    if (score === 0) score = 1;                          // matched only via romanized/cyrillic form
    exactIds.add(s.id);
    scored.push({ s, score });
  }

  // --- Step 2: fuzzy (typo tolerance) — only when exact is sparse and q is long enough ---
  if (q && q.length >= 3 && scored.length < FUZZY_WHEN_FEWER_THAN) {
    buildFuzzy(data);
    const fuzzyBest = new Map<string, number>();
    for (const res of _fuse!.search(q)) {
      const ids = _wordToIds.get(res.item.word);
      if (!ids) continue;
      const sc = res.score ?? 1;
      for (const id of ids) {
        if (sc < (fuzzyBest.get(id) ?? 1)) fuzzyBest.set(id, sc);
      }
    }
    for (const [id, fuseScore] of fuzzyBest) {
      if (exactIds.has(id)) continue;
      const s = _byId.get(id);
      if (!s || !passesFilters(s, filters)) continue;
      scored.push({ s, score: (1 - fuseScore) * 0.5 }); // capped < exact so exact ranks first
    }
  }

  // --- Step 3: sort ---
  if (sort === "random") {
    const arr = scored.map((x) => x.s);
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }
  scored.sort((a, b) => {
    if (q && b.score !== a.score) return b.score - a.score;
    if (sort === "newest") return b.s.uploadDate.localeCompare(a.s.uploadDate);
    return (b.s.viewCount ?? 0) - (a.s.viewCount ?? 0);
  });
  return scored.map((x) => x.s);
}
