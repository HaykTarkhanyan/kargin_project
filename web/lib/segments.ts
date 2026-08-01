import { normalize, fold } from "./normalize";
import { romanize, cyrillize } from "./translit";

// `text` is stored as one string; these are the real separators in the curated
// data. Mirrors _LINE_SPLIT in scripts/kargin_build/parse.py — deliberately NOT
// a bare '-', which would mangle "1-2".
const LINE_SPLIT = /[;։]/;

export function textLines(text: string): string[] {
  return text.split(LINE_SPLIT).map((s) => s.trim()).filter(Boolean);
}

export interface Segment {
  text: string;
  /** Whether this line matched the query, by any script. */
  matched: boolean;
  /**
   * [start, end) offsets of the query inside `text`, for highlighting.
   * Empty when the line matched only via a transliterated form: romanization
   * changes length (ու -> u is 2 chars to 1), so an offset in the romanized
   * string does not map back to the original. Such lines are still flagged
   * `matched`, just without an inner highlight.
   */
  hits: Array<[number, number]>;
}

function hitsIn(line: string, q: string): Array<[number, number]> {
  const hay = fold(line);            // offset-preserving, unlike normalize()
  const out: Array<[number, number]> = [];
  for (let i = hay.indexOf(q); i !== -1; i = hay.indexOf(q, i + q.length)) {
    out.push([i, i + q.length]);
  }
  return out;
}

/**
 * Split `text` into dialogue lines and mark which ones the query hits.
 *
 * Search matches against Armenian + romanized + Cyrillic forms at once, so a
 * Latin query legitimately matches an Armenian line. Transliteration is only
 * attempted when the direct search misses, keeping the common case to one
 * `indexOf` per line.
 */
export function segmentsFor(text: string, query: string): Segment[] {
  const lines = textLines(text);
  const q = normalize(query);
  if (!q) return lines.map((t) => ({ text: t, matched: false, hits: [] }));

  return lines.map((line) => {
    const hits = hitsIn(line, q);
    const matched =
      hits.length > 0 ||
      normalize(romanize(line)).includes(q) ||
      normalize(cyrillize(line)).includes(q);
    return { text: line, matched, hits };
  });
}

/** Matched lines first, original order preserved within each group. */
export function matchedFirst(segments: Segment[]): Segment[] {
  if (!segments.some((s) => s.matched)) return segments;
  return [...segments.filter((s) => s.matched), ...segments.filter((s) => !s.matched)];
}
