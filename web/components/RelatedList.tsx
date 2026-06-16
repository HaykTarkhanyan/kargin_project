import Link from "next/link";
import type { Sketch } from "@/lib/types";
import { formatViews } from "@/lib/format";

export default function RelatedList({ items }: { items: Sketch[] }) {
  return (
    <div>
      {items.map((s) => (
        <Link key={s.id} href={`/sketch/${s.id}`} className="flex items-center gap-3 border-b border-dashed border-ink/15 py-2.5 last:border-0 hover:opacity-80">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={s.thumbnail} alt={s.title} loading="lazy" className="h-9 w-16 shrink-0 rounded border-2 border-ink object-cover" />
          <div className="min-w-0">
            <div className="truncate text-xs font-bold">{s.title}</div>
            <div className="text-[10px] font-semibold text-muted">{s.location} · {formatViews(s.viewCount)} դիտում</div>
          </div>
        </Link>
      ))}
    </div>
  );
}
