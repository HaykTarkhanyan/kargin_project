import type { Sketch } from "./types";

export function related(target: Sketch, all: Sketch[], limit = 6): Sketch[] {
  const freq: Record<string, number> = {};
  for (const s of all) for (const a of s.actors) freq[a] = (freq[a] ?? 0) + 1;

  const scored = all
    .filter((s) => s.id !== target.id)
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

  const have = new Set(hits.map((s) => s.id));
  const fill = all
    .filter((s) => s.id !== target.id && !have.has(s.id))
    .sort((a, b) => (b.viewCount ?? 0) - (a.viewCount ?? 0))
    .slice(0, limit - hits.length);
  return [...hits, ...fill];
}
