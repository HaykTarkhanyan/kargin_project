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
    <Link href={`/sketch/${s.id}`} className="group block overflow-hidden rounded-xl k-border k-shadow transition hover:-translate-x-[3px] hover:-translate-y-[3px] hover:k-shadow-red bg-card">
      <div className="relative aspect-video border-b-2 border-ink bg-paper2">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={s.thumbnail} alt={s.title} loading="lazy" className="absolute inset-0 h-full w-full object-cover" />
        <span className="absolute left-2 top-2 rounded-full bg-kblue px-2.5 py-1 text-[11px] font-bold text-white">{s.location}</span>
        <span className="absolute bottom-2 right-2 rounded bg-ink px-2 py-0.5 text-[11px] font-bold text-paper">{formatDuration(s.durationSec)}</span>
      </div>
      <div className="p-4">
        <div className="mb-2 font-bold leading-snug">{s.title}</div>

        {quoteSegment && (
          <div className="mb-2 border-l-[3px] border-korange pl-3 text-sm opacity-75">
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
            <div className="mb-3 max-h-36 space-y-1 overflow-y-auto border-l-[3px] border-ink/25 pl-3 pr-1 text-sm leading-relaxed">
              {segments.map((seg, i) => (
                <p key={i} className={seg.matched ? "font-semibold" : "opacity-65"}>
                  <Highlight segment={seg} />
                </p>
              ))}
            </div>
          </>
        )}

        <div className="flex items-center gap-2 text-xs font-semibold text-muted">
          <span>{s.actors.join(" ")}</span><span className="opacity-50">·</span>
          <span className="text-ink">{formatViews(s.viewCount)} դիտում</span>
        </div>
      </div>
    </Link>
  );
}
