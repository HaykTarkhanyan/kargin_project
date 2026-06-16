import Link from "next/link";
import type { Sketch } from "@/lib/types";
import { formatViews, formatDuration } from "@/lib/format";

export default function SketchCard({ sketch: s, snippet }: { sketch: Sketch; snippet?: string }) {
  const quote = snippet ?? s.textCommon ?? "";
  return (
    <Link href={`/sketch/${s.id}`} className="group block overflow-hidden rounded-xl k-border k-shadow transition hover:-translate-x-[3px] hover:-translate-y-[3px] hover:k-shadow-red bg-card">
      <div className="relative aspect-video border-b-2 border-ink bg-cover bg-center" style={{ backgroundImage: `url(${s.thumbnail})` }}>
        <span className="absolute left-2 top-2 rounded-full bg-kblue px-2.5 py-1 text-[11px] font-bold text-white">{s.location}</span>
        <span className="absolute bottom-2 right-2 rounded bg-ink px-2 py-0.5 text-[11px] font-bold text-paper">{formatDuration(s.durationSec)}</span>
      </div>
      <div className="p-4">
        <div className="mb-2 font-bold leading-snug">{s.title}</div>
        {quote && <div className="mb-3 border-l-[3px] border-korange pl-3 text-sm opacity-75">«{quote}»</div>}
        <div className="flex items-center gap-2 text-xs font-semibold text-muted">
          <span>{s.actors.join(" ")}</span><span className="opacity-50">·</span>
          <span className="text-ink">{formatViews(s.viewCount)} դիտում</span>
        </div>
      </div>
    </Link>
  );
}
