import type { Segment } from "@/lib/segments";

/**
 * Render a dialogue line with the matched substrings marked.
 *
 * No hooks, so this stays usable from server components (SketchGrid renders
 * cards at build time on the actor pages).
 *
 * The <mark> pins an explicit dark ink colour rather than using `text-ink`:
 * --orange is the same #F2A800 in both themes, so the themed ink would flip to
 * near-white on dark and drop the contrast to unreadable.
 */
export default function Highlight({ segment }: { segment: Segment }) {
  if (!segment.hits.length) return <>{segment.text}</>;

  const parts: React.ReactNode[] = [];
  let cursor = 0;
  segment.hits.forEach(([start, end], i) => {
    if (start > cursor) parts.push(segment.text.slice(cursor, start));
    parts.push(
      <mark key={i} className="rounded-[3px] bg-korange px-0.5 font-bold text-[#1A1410]">
        {segment.text.slice(start, end)}
      </mark>,
    );
    cursor = end;
  });
  if (cursor < segment.text.length) parts.push(segment.text.slice(cursor));
  return <>{parts}</>;
}
