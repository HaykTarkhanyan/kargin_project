import Link from "next/link";
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

// Presentational only — tiles are computed at build time in the server page,
// so this ships no client JS and never pulls the sketch dataset into the bundle.
export default function Soundboard({ tiles }: { tiles: PhraseTile[] }) {
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
