import { ALL } from "@/lib/data";
import { normalize } from "@/lib/search";

export interface PhraseTile {
  phrase: string;
  count: number;
  sketchId: string;
  sketchTitle: string;
}

/**
 * For each phrase, find the most-viewed sketch whose normalized
 * (text + " " + textCommon) contains the normalized phrase.
 * Returns only tiles where a matching sketch was found.
 */
export function buildPhraseTiles(
  topPhrases: { p: string; n: number }[]
): PhraseTile[] {
  const tiles: PhraseTile[] = [];

  for (const { p, n } of topPhrases) {
    const normalizedPhrase = normalize(p);

    let best: { sketch: (typeof ALL)[number]; views: number } | null = null;

    for (const sketch of ALL) {
      const haystack = normalize(sketch.text + " " + sketch.textCommon);
      if (!haystack.includes(normalizedPhrase)) continue;

      const views = sketch.viewCount ?? 0;
      if (!best || views > best.views) {
        best = { sketch, views };
      }
    }

    if (best) {
      tiles.push({
        phrase: p,
        count: n,
        sketchId: best.sketch.id,
        sketchTitle: best.sketch.title,
      });
    }
  }

  return tiles;
}
