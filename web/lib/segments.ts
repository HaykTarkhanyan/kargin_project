import { normalize, fold } from "./normalize";
import { romanize, cyrillize } from "./translit";

// `text` is stored as one string; `;` and `։` are the real separators in the
// curated data. Mirrors _LINE_SPLIT in scripts/kargin_build/parse.py —
// deliberately NOT a bare '-', which would mangle "1-2".
//
// Newline is in here for the machine transcripts, which are the other thing
// callers pass in and which separate their lines that way. Without it a
// transcript comes back as two or three enormous "lines".
const LINE_SPLIT = /[;։\n]/;

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

const WORD_SPLIT = /[^\p{L}\p{N}]+/u;

/** Sorted and non-overlapping, which is what Highlight's cursor walk assumes. */
function mergeRanges(ranges: Array<[number, number]>): Array<[number, number]> {
  if (ranges.length < 2) return ranges;
  const sorted = [...ranges].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const out: Array<[number, number]> = [sorted[0]];
  for (const [start, end] of sorted.slice(1)) {
    const last = out[out.length - 1];
    if (start <= last[1]) last[1] = Math.max(last[1], end);
    else out.push([start, end]);
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

  // Search matches a phrase word by word, so highlighting has to as well: a card
  // returned for a half-remembered line would otherwise show nothing marked and
  // no reason it was there.
  const words = q.split(WORD_SPLIT).filter(Boolean);

  return lines.map((line) => {
    const hits = hitsIn(line, q);
    if (hits.length) return { text: line, matched: true, hits };
    if (words.length > 1) {
      const perWord = mergeRanges(words.flatMap((w) => hitsIn(line, w)));
      if (perWord.length) return { text: line, matched: true, hits: perWord };
    }
    const matched =
      normalize(romanize(line)).includes(q) ||
      normalize(cyrillize(line)).includes(q);
    return { text: line, matched, hits: [] };
  });
}

/**
 * Matched lines first, the fullest match leading, original order kept within
 * each group.
 *
 * Ordering by how much of the query a line actually covers matters once a phrase
 * matches word by word: with "պապա պտի ասես" every line holding a bare "պտի"
 * counts as matched, and a plain matched/unmatched split would leave the line
 * carrying the whole phrase buried among them.
 */
export function matchedFirst(segments: Segment[]): Segment[] {
  if (!segments.some((s) => s.matched)) return segments;
  const covered = (s: Segment) => s.hits.reduce((n, [start, end]) => n + (end - start), 0);
  const matched = segments.filter((s) => s.matched);
  const best = Math.max(...matched.map(covered));
  // A stable partition rather than a sort, so lines tying on coverage stay in
  // the order they are spoken.
  return [
    ...matched.filter((s) => covered(s) === best),
    ...matched.filter((s) => covered(s) !== best),
    ...segments.filter((s) => !s.matched),
  ];
}
