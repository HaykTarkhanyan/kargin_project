"use client";

import { useMemo } from "react";
import Link from "next/link";
import { ALL } from "@/lib/data";
import { STATS } from "@/lib/stats-data";
import { normalize } from "@/lib/search";
import type { PhraseTile } from "@/lib/soundboard";

// Accent colors cycling through flag palette
const ACCENTS: Array<{ border: string; shadow: string; label: string }> = [
  { border: "border-kred",    shadow: "shadow-kred",    label: "text-kred"    },
  { border: "border-kblue",   shadow: "shadow-kblue",   label: "text-kblue"   },
  { border: "border-korange", shadow: "shadow-korange", label: "text-korange" },
];

// Tile size classes — vary by position for a "wall" feel
const SIZE_CLASSES = [
  "text-2xl py-5 px-5",
  "text-xl  py-4 px-4",
  "text-lg  py-4 px-4",
  "text-xl  py-5 px-5",
  "text-2xl py-4 px-4",
  "text-lg  py-5 px-5",
];

export default function Soundboard() {
  const tiles: PhraseTile[] = useMemo(() => {
    const result: PhraseTile[] = [];
    for (const { p, n } of STATS.topPhrases) {
      const normalizedPhrase = normalize(p);
      let best: { id: string; title: string; views: number } | null = null;

      for (const sketch of ALL) {
        const haystack = normalize(sketch.text + " " + sketch.textCommon);
        if (!haystack.includes(normalizedPhrase)) continue;
        const views = sketch.viewCount ?? 0;
        if (!best || views > best.views) {
          best = { id: sketch.id, title: sketch.title, views };
        }
      }

      if (best) {
        result.push({ phrase: p, count: n, sketchId: best.id, sketchTitle: best.title });
      }
    }
    return result;
  }, []);

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
      {tiles.map((tile, i) => {
        const accent = ACCENTS[i % ACCENTS.length];
        const size = SIZE_CLASSES[i % SIZE_CLASSES.length];
        return (
          <Link
            key={tile.phrase}
            href={`/sketch/${tile.sketchId}`}
            className={[
              "k-border k-shadow group flex flex-col items-start rounded-lg bg-card",
              "transition-transform duration-150 hover:-translate-y-0.5 hover:scale-[1.02]",
              size,
            ].join(" ")}
          >
            <span className="font-display leading-tight text-ink">
              «{tile.phrase}»
            </span>
            <span className={["mt-2 text-xs font-bold uppercase tracking-widest", accent.label].join(" ")}>
              {tile.count}× սքեթչ
            </span>
          </Link>
        );
      })}
    </div>
  );
}
