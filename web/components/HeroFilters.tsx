"use client";
import type { Facets } from "@/lib/facets";
import { sortedEntries } from "@/lib/facets";
import type { Filters } from "@/lib/search";

export default function HeroFilters({ facets, filters, setFilters }:
  { facets: Facets; filters: Filters; setFilters: (f: Filters) => void }) {
  const toggle = (k: "location" | "actors" | "language", v: string) => {
    const cur = filters[k] ?? [];
    setFilters({ ...filters, [k]: cur.includes(v) ? cur.filter((x) => x !== v) : [...cur, v] });
  };
  return (
    <div className="k-border k-shadow rounded-lg bg-paper2 p-4">
      <div className="mb-2 font-display text-base tracking-wide">ԶՏԻՉՆԵՐ</div>
      <Group title="Վայր" entries={sortedEntries(facets.location).slice(0, 6)} sel={filters.location ?? []} on={(v) => toggle("location", v)} />
      <Group title="Դերասան" entries={sortedEntries(facets.actors).slice(0, 6)} sel={filters.actors ?? []} on={(v) => toggle("actors", v)} />
      <Group title="Լեզու" entries={sortedEntries(facets.language).slice(0, 4)} sel={filters.language ?? []} on={(v) => toggle("language", v)} />
    </div>
  );
}
function Group({ title, entries, sel, on }:
  { title: string; entries: [string, number][]; sel: string[]; on: (v: string) => void }) {
  return (
    <details className="border-t border-ink/15 py-1.5" open={sel.length > 0}>
      <summary className="cursor-pointer text-[11px] font-extrabold uppercase tracking-widest">{title}{sel.length ? ` (${sel.length})` : ""}</summary>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {entries.map(([name, count]) => (
          <button key={name} onClick={() => on(name)} className={`rounded-full border-2 border-ink px-2.5 py-1 text-xs font-semibold ${sel.includes(name) ? "bg-kblue text-white" : "bg-surface"}`}>
            {name} <span className="opacity-60">{count}</span>
          </button>
        ))}
      </div>
    </details>
  );
}
