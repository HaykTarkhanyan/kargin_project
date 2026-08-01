/**
 * Text normalization shared by search, name-finding and segment highlighting.
 *
 * Lives in its own module because `search.ts` imports Fuse.js: anything that
 * needed only `normalize` was dragging the whole fuzzy-search library into its
 * bundle, including server components that never search at all.
 */

/** Lowercase + NFC + collapse whitespace. Changes length, so NOT for offsets. */
export function normalize(s: string): string {
  return s.toLowerCase().normalize("NFC").replace(/\s+/g, " ").trim();
}

/**
 * Case/composition fold that PRESERVES character offsets, for locating a match
 * inside the original string so it can be highlighted. `normalize` collapses
 * whitespace and would shift every index after the first run of spaces.
 */
export function fold(s: string): string {
  return s.toLowerCase().normalize("NFC");
}
