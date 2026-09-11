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

// Word boundary for both the query and the index. `normalize` deliberately keeps
// punctuation (offsets matter elsewhere), so splitting on non-letters is what
// makes "երկու" match the stored "երկու," — the comma is not part of the word.
const WORD_SPLIT = /[^\p{L}\p{N}]+/u;

function toWords(s: string): string[] {
  return s.split(WORD_SPLIT).filter(Boolean);
}

/** Characters allowed between consecutive query words when scoring a near-phrase. */
const PHRASE_GAP = 40;
/** Restarts allowed when looking for a near-phrase, so a stopword cannot make it quadratic. */
const PHRASE_STARTS = 64;

/**
 * True when every word occurs in order, each starting within `gap` characters of
 * the end of the previous one. Restarts at each occurrence of the first word,
 * because the earliest occurrence is not always the one in the right sentence.
 */
function orderedWithin(hay: string, words: string[], gap: number): boolean {
  let starts = 0;
  for (let at = hay.indexOf(words[0]); at !== -1; at = hay.indexOf(words[0], at + 1)) {
    if (++starts > PHRASE_STARTS) return false;
    let from = at + words[0].length;
    let ok = true;
    for (let i = 1; i < words.length; i++) {
      const next = hay.indexOf(words[i], from);
      if (next === -1 || next - from > gap) { ok = false; break; }
      from = next + words[i].length;
    }
    if (ok) return true;
  }
  return false;
}

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
// Word index — every unique word mapped back to the sketches containing it,
// plus the vocabulary bucketed by word length so a misspelling only has to be
// compared against words that could plausibly be it. Built once per dataset,
// and only when a query actually needs it: most never get past the exact pass.
// ---------------------------------------------------------------------------
let _indexedData: Sketch[] | null = null;
let _wordToIds: Map<string, Set<string>> = new Map();
let _wordsByLength: Map<number, string[]> = new Map();
let _byId: Map<string, Sketch> = new Map();

function buildWordIndex(data: Sketch[]): void {
  if (_indexedData === data) return;
  _indexedData = data;
  _wordToIds = new Map();
  _wordsByLength = new Map();
  _byId = new Map();
  for (const s of data) {
    _byId.set(s.id, s);
    // Split on punctuation, not spaces: a plain space split leaves "երկու," and
    // "երկու" as different entries, which the word lookups could not reconcile.
    for (const word of toWords(getIndex(s).combined)) {
      if (word.length < 2) continue;
      let set = _wordToIds.get(word);
      if (!set) {
        set = new Set();
        _wordToIds.set(word, set);
        const bucket = _wordsByLength.get(word.length);
        if (bucket) bucket.push(word);
        else _wordsByLength.set(word.length, [word]);
      }
      set.add(s.id);
    }
  }
}

const SPARSE_RESULTS = 12; // below this, widen the search rather than show almost nothing

/** Candidates whose word positions get checked. Proximity only reorders the head. */
const PROXIMITY_LIMIT = 60;
// Thresholds are fractions of log(corpus size) — the weight of a word unique to
// one sketch — rather than absolute numbers, because word weights scale with the
// size of the archive. Hard-coding them for 702 sketches made the whole pass go
// quiet on any smaller set.
/** Under this a query is all filler ("որ", "եմ") and every sketch would qualify. */
const MIN_QUERY_INFO = 0.18;
/** Floor on what a sketch must match, so a lone common word is never enough. */
const MIN_MATCH_INFO = 0.38;
/** A word this distinctive (roughly under 1% of sketches) identifies one on its own. */
const DECISIVE_MATCH_INFO = 0.69;
/** Otherwise several words must cover most of what the query means. */
const MIN_MATCH_SHARE = 0.45;
/**
 * Levenshtein distance, abandoned once it is certain to exceed `max`.
 *
 * This is what decides whether a word is a misspelling of another. Fuse's Bitap
 * score saturates on short words — it handed the same 0.25 to "սամո" (one
 * substitution, the sketch the visitor actually wanted) and to "կարող", "պարոն"
 * and 457 others, so no score threshold could separate them.
 */
function editDistance(a: string, b: string, max: number): number {
  if (Math.abs(a.length - b.length) > max) return max + 1;
  let prev = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    const cur: number[] = [i];
    let best = i;
    for (let j = 1; j <= b.length; j++) {
      cur[j] = Math.min(
        prev[j] + 1,
        cur[j - 1] + 1,
        prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1),
      );
      if (cur[j] < best) best = cur[j];
    }
    if (best > max) return max + 1;
    prev = cur;
  }
  return prev[b.length];
}

/** How far a near-spelling may stray: one edit, plus one per four characters. */
function fuzzyTolerance(word: string): number {
  return Math.max(1, Math.floor(word.length / 4));
}

/** Only words at least this distinctive are worth a fuzzy expansion. */
const FUZZY_MAX_SHARE = 0.05;
/** Shorter than this, near-spellings are too numerous to mean anything. */
const FUZZY_MIN_LENGTH = 3;

/** Weight of a near-spelling against the word itself, before the distance taper. */
const FUZZY_WEIGHT = 0.8;

/**
 * Which word of a phrase is worth spending a fuzzy expansion on: one the archive
 * never says (so it was likely misremembered), else the rarest that is still
 * distinctive. Returns -1 when every word is common, where expanding adds noise.
 */
function rarestWordIndex(words: string[], hit: Array<Map<Sketch, number>>, total: number): number {
  let best = -1;
  let bestCount = Infinity;
  words.forEach((w, i) => {
    if (w.length < FUZZY_MIN_LENGTH) return;
    const count = hit[i].size;
    if (count === 0) { if (bestCount > 0) { best = i; bestCount = 0; } return; }
    if (count < bestCount && count <= total * FUZZY_MAX_SHARE) { best = i; bestCount = count; }
  });
  return best;
}

/**
 * Sketches reachable from `word` by a small misspelling, with the edit distance.
 *
 * Only words of a comparable length can be within the tolerance, so the scan
 * skips the rest of the vocabulary outright. Measured on the 702-sketch archive:
 * 85-130 ms here against 481-1096 ms for the Fuse pass this replaced, and far
 * more precise — Fuse offered 195 candidates for "կառնեմ" where 8 are actually
 * within one edit, and its score could not tell them apart.
 */
function nearSpellings(word: string, data: Sketch[]): Map<Sketch, number> {
  buildWordIndex(data);
  const tolerance = fuzzyTolerance(word);
  const out = new Map<Sketch, number>();
  for (let len = word.length - tolerance; len <= word.length + tolerance; len++) {
    for (const candidate of _wordsByLength.get(len) ?? []) {
      const away = editDistance(word, candidate, tolerance);
      if (away > tolerance || away === 0) continue;
      for (const id of _wordToIds.get(candidate) ?? []) {
        const s = _byId.get(id);
        if (s && away < (out.get(s) ?? Infinity)) out.set(s, away);
      }
    }
  }
  return out;
}

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

  // --- Step 2: scattered words — the query's words are all there, just not adjacent ---
  // Someone recalling a line types it as they remember it; the archive stores it
  // with different commas and filler, so the exact pass above finds nothing.
  // Match on the words instead, and rank by how many hit and how close together.
  const qWords = toWords(q);
  const seen = new Set(exactIds);
  const widen = qWords.length >= 2 && scored.length < SPARSE_RESULTS;

  // Each word is matched the same way step 1 matches the whole query — as a
  // substring, not a whole word. Armenian glues its suffixes on ("անու" inside
  // "անում"), and a word-boundary index quietly lost matches the exact pass
  // would have found. The value is how strongly the word matched: 1 for the word
  // itself, less for a near-spelling filled in below.
  const hit: Array<Map<Sketch, number>> = qWords.map(() => new Map());
  // How rare each word really is, counted before near-spellings are folded in —
  // otherwise expanding a rare word inflates its document count and destroys the
  // very rarity that made it worth expanding.
  const trueCount: number[] = qWords.map(() => 0);
  if (widen) {
    for (const s of data) {
      if (!passesFilters(s, filters)) continue;
      const hay = getIndex(s).combined;
      qWords.forEach((w, i) => { if (hay.includes(w)) hit[i].set(s, 1); });
    }
    qWords.forEach((_, i) => { trueCount[i] = hit[i].size; });
    // One word may be misspelled — the visitor who wanted the role "Սամո" typed
    // "սարո". Fuzzing the phrase's rarest word (never its filler, which cost
    // seconds and returned 645 sketches) feeds those sketches into the same
    // scoring below, so matching a near-spelling AND another word of the query
    // beats matching either alone.
    const slot = rarestWordIndex(qWords, hit, data.length);
    if (slot !== -1) {
      for (const [s, away] of nearSpellings(qWords[slot], data)) {
        if (!hit[slot].has(s) && passesFilters(s, filters)) {
          hit[slot].set(s, FUZZY_WEIGHT / away);
        }
      }
    }
  }

  if (widen) {
    // Words are weighted by how rare they are (inverse document frequency).
    // Counting words equally does not work here: "որ" and "եմ" are in almost
    // every sketch, so "պապա պտի ասես" matched 538 of 702 on filler alone. A word
    // in every sketch scores ~0 and a rare one dominates, which puts the
    // requirement on the words that actually carry the meaning.
    const matched = new Map<Sketch, number>();
    const hitCount = new Map<Sketch, number>();
    let queryInfo = 0;
    hit.forEach((found, i) => {
      // A word nobody in the archive says — a misremembered one — is dropped
      // rather than counted as unmatchable, or one wrong word would zero the query.
      if (!found.size) return;
      const idf = Math.log(data.length / (trueCount[i] || found.size));
      queryInfo += idf;
      for (const [s, weight] of found) {
        matched.set(s, (matched.get(s) ?? 0) + idf * weight);
        hitCount.set(s, (hitCount.get(s) ?? 0) + 1);
      }
    });

    const unit = Math.log(data.length) || 1; // weight of a word unique to one sketch
    if (queryInfo >= MIN_QUERY_INFO * unit) {
      const candidates: Array<{ s: Sketch; share: number }> = [];
      for (const [s, got] of matched) {
        if (seen.has(s.id) || got < MIN_MATCH_INFO * unit) continue;
        // Either one word rare enough to pin the sketch down on its own
        // ("կառնեմ", in 6 of 702), or several words covering most of the query.
        const share = got / queryInfo;
        const decisive = got >= DECISIVE_MATCH_INFO * unit;
        const broad = (hitCount.get(s) ?? 0) >= 2 && share >= MIN_MATCH_SHARE;
        if (!decisive && !broad) continue;
        candidates.push({ s, share });
      }
      // Only the strongest candidates pay for a position scan; below the head it
      // cannot change what the visitor actually sees.
      candidates.sort((a, b) => b.share - a.share);
      candidates.forEach(({ s, share }, rank) => {
        seen.add(s.id);
        const nearby =
          rank < PROXIMITY_LIMIT &&
          share > 0.999 &&
          orderedWithin(getIndex(s).combined, qWords, PHRASE_GAP);
        // 0.5..0.95 — always under the exact pass's floor of 1, so a literal
        // match never loses to a scattered one.
        scored.push({ s, score: 0.5 + share * 0.25 + (nearby ? 0.2 : 0) });
      });
    }
  }

  // --- Step 3: fuzzy for a single-word query ---
  // A phrase already had its rarest word fuzzed into the scoring above, where a
  // near-spelling can combine with the query's other words. A lone word has
  // nothing to combine with, so it gets its own tier below every real match.
  if (q && q.length >= 3 && qWords.length <= 1 && scored.length < SPARSE_RESULTS) {
    const tolerance = fuzzyTolerance(q);
    for (const [s, away] of nearSpellings(q, data)) {
      if (seen.has(s.id) || !passesFilters(s, filters)) continue;
      seen.add(s.id);
      // Under the word pass's floor, so a real match always outranks a guess.
      scored.push({ s, score: (0.4 * (tolerance + 1 - away)) / (tolerance + 1) });
    }
  }

  // --- Step 4: sort ---
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
