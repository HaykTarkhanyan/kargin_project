/**
 * Text normalization shared by search, name-finding and segment highlighting.
 *
 * Lives in its own module so that anything needing only `normalize` does not
 * pull in the whole search index with it — server components that never search
 * at all were importing the lot.
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
