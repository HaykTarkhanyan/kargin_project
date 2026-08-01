import Link from "next/link";
import type { Sketch } from "@/lib/types";
import { formatViews, formatDuration } from "@/lib/format";
import { segmentsFor, matchedFirst } from "@/lib/segments";
import Highlight from "./Highlight";

export default function SketchCard({
  sketch: s,
  snippet,
  query,
}: {
  sketch: Sketch;
  snippet?: string;
  /** Active search query — matching dialogue lines are surfaced and highlighted. */
  query?: string;
}) {
  const q = query?.trim() ?? "";
  const quote = snippet ?? s.textCommon ?? "";
  // Matched lines float to the top so the reason a sketch is in the results is
  // visible without scrolling the dialogue box.
  const segments = matchedFirst(segmentsFor(s.text, q));
  const matchCount = segments.filter((seg) => seg.matched).length;
  const quoteSegment = quote ? segmentsFor(quote, q)[0] : undefined;

  return (
    // flex column so the dialogue box can absorb the height the grid row gives
    // this card; otherwise a short sketch next to a long one leaves dead space.
    <Link href={`/sketch/${s.id}`} className="group flex h-full flex-col overflow-hidden rounded-xl k-border k-shadow transition hover:-translate-x-[3px] hover:-translate-y-[3px] hover:k-shadow-red bg-card">
      <div className="relative aspect-video border-b-2 border-ink bg-paper2">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={s.thumbnail} alt={s.title} loading="lazy" className="absolute inset-0 h-full w-full object-cover" />
        <span className="absolute left-2 top-2 rounded-full bg-kblue px-2.5 py-1 text-[11px] font-bold text-white">{s.location}</span>
        <span className="absolute bottom-2 right-2 rounded bg-ink px-2 py-0.5 text-[11px] font-bold text-paper">{formatDuration(s.durationSec)}</span>
        {!!s.songs?.length && (
          <span title={s.songs.map((x) => `${x.artist} — ${x.title}`).join("\n")}
            className="absolute bottom-2 left-2 rounded bg-korange px-1.5 py-0.5 text-[11px] font-bold text-[#1A1410]">
            🎵 {s.songs.length}
          </span>
        )}
      </div>
      <div className="flex flex-1 flex-col p-4">
        <div className="mb-2 font-bold leading-snug">{s.title}</div>

        {/* line-clamp keeps an unusually long catchphrase from setting the
            height of every card in its grid row. */}
        {quoteSegment && (
          <div className="mb-2 line-clamp-3 border-l-[3px] border-korange pl-3 text-sm opacity-75">
            «<Highlight segment={quoteSegment} />»
          </div>
        )}

        {segments.length > 0 && (
          <>
            {q && matchCount > 0 && (
              <div className="mb-1.5 text-[11px] font-bold text-kred">
                {matchCount} համընկնում
              </div>
            )}
            <div className="mb-3 max-h-36 min-h-0 flex-1 space-y-1 overflow-y-auto border-l-[3px] border-ink/25 pl-3 pr-1 text-sm leading-relaxed">
              {segments.map((seg, i) => (
                <p key={i} className={seg.matched ? "font-semibold" : "opacity-65"}>
                  <Highlight segment={seg} />
                </p>
              ))}
            </div>
          </>
        )}

        {/* mt-auto pins the footer to the card bottom, so sketches with no
            dialogue (nothing to flex) don't leave a gap under their meta row. */}
        <div className="mt-auto flex items-center gap-2 text-xs font-semibold text-muted">
          <span>{s.actors.join(" ")}</span><span className="opacity-50">·</span>
          <span className="text-ink">{formatViews(s.viewCount)} դիտում</span>
        </div>
      </div>
    </Link>
  );
}
