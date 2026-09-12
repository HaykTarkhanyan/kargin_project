import type { Sketch } from "./types";

// Actor-frequency table memoized by dataset identity — `related` is called once
// per sketch page, and rebuilding this over all sketches each time is pure waste.
let _freqFor: Sketch[] | null = null;
let _freq: Record<string, number> = {};
function actorFreq(all: Sketch[]): Record<string, number> {
  if (_freqFor === all) return _freq;
  const f: Record<string, number> = {};
  for (const s of all) for (const a of s.actors) f[a] = (f[a] ?? 0) + 1;
  _freqFor = all;
  _freq = f;
  return f;
}

// Same memo trick for id lookup, used to resolve `similar` ids to sketches.
let _byIdFor: Sketch[] | null = null;
let _byId: Map<string, Sketch> = new Map();
function byId(all: Sketch[]): Map<string, Sketch> {
  if (_byIdFor === all) return _byId;
  _byId = new Map(all.map((s) => [s.id, s]));
  _byIdFor = all;
  return _byId;
}

/** Actor-overlap ranking, rare co-stars weighted highest. The fallback since 2026-06. */
function byActors(target: Sketch, all: Sketch[], limit: number, exclude: Set<string>): Sketch[] {
  const freq = actorFreq(all);

  const scored = all
    .filter((s) => s.id !== target.id && !exclude.has(s.id))
    .map((s) => {
      let score = 0;
      for (const a of target.actors) if (s.actors.includes(a)) score += 1 / (freq[a] || 1);
      if (target.location !== "Այլ" && s.location === target.location) score += 0.05;
      return { s, score };
    });

  const hits = scored
    .filter((x) => x.score > 0)
    .sort((a, b) => b.score - a.score || (b.s.viewCount ?? 0) - (a.s.viewCount ?? 0))
    .map((x) => x.s);

  if (hits.length >= limit) return hits.slice(0, limit);

  const have = new Set([...exclude, ...hits.map((s) => s.id)]);
  const fill = all
    .filter((s) => s.id !== target.id && !have.has(s.id))
    .sort((a, b) => (b.viewCount ?? 0) - (a.viewCount ?? 0))
    .slice(0, limit - hits.length);
  return [...hits, ...fill];
}

/**
 * Sketches to show under "ՆՄԱՆԱՏԻՊ", best first.
 *
 * Semantic neighbours lead: `similar` is precomputed from embeddings of the
 * detailed summaries, so it matches on what the sketch is ABOUT — two different
 * casts doing confession-to-a-priest rank together, which actor overlap can
 * never see. It is deliberately short or absent (only 292 of 702 sketches have a
 * match above the cosine floor), so actor overlap fills the rest and the section
 * is never empty — the behaviour the page had before.
 */
export function related(target: Sketch, all: Sketch[], limit = 6): Sketch[] {
  const lookup = byId(all);
  const semantic = (target.similar ?? [])
    .map((n) => lookup.get(n.id))
    .filter((s): s is Sketch => s !== undefined && s.id !== target.id)
    .slice(0, limit);

  if (semantic.length >= limit) return semantic;
  const taken = new Set(semantic.map((s) => s.id));
  return [...semantic, ...byActors(target, all, limit - semantic.length, taken)];
}
