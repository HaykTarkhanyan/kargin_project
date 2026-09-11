/**
 * Hearts — "I love this one".
 *
 * Two halves, deliberately separate:
 *   - the visitor's own hearts live in localStorage, so the button remembers
 *     across visits without an account and without a round trip;
 *   - each CHANGE is logged to Firestore as an event, so a ranking can be built
 *     from it later.
 *
 * Both directions are logged. Counting only the hearts would leave a sketch
 * credited for a tap somebody immediately took back, and the whole point of
 * collecting this is to end up with a number worth trusting.
 *
 * One device is one voice: the same person on a phone and a laptop counts twice,
 * and clearing site data resets them. That is the honest ceiling of storing this
 * without accounts, and it is why no count is shown anywhere yet.
 */
import { logEvent } from "./log";

const KEY = "kargin_hearts";

/** Fires when this tab changes the set, so every heart on the page can re-read it. */
export const HEARTS_CHANGED = "kargin:hearts";

export function readHearts(): Set<string> {
  try {
    const raw = localStorage.getItem(KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return new Set(Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === "string") : []);
  } catch {
    // Private mode, disabled storage, corrupted value — a lost heart is not
    // worth breaking the page over.
    return new Set();
  }
}

function write(ids: Set<string>): void {
  try {
    localStorage.setItem(KEY, JSON.stringify([...ids]));
  } catch (e) {
    console.warn("kargin hearts: could not save", e);
  }
}

/** Toggle one sketch and announce the change. Returns the new state. */
export function toggleHeart(sketchId: string, source: string): boolean {
  const ids = readHearts();
  const hearted = !ids.has(sketchId);
  if (hearted) ids.add(sketchId);
  else ids.delete(sketchId);
  write(ids);
  logEvent(hearted ? "heart" : "unheart", { sketchId, source });
  window.dispatchEvent(new CustomEvent(HEARTS_CHANGED));
  return hearted;
}
