"use client";
import type { Facets } from "@/lib/facets";
import { sortedEntries } from "@/lib/facets";
import type { Filters } from "@/lib/search";

export default function FilterRail({ facets, filters, setFilters }:
  { facets: Facets; filters: Filters; setFilters: (f: Filters) => void }) {
  const toggle = (k: "location" | "actors" | "language", v: string) => {
    const cur = filters[k] ?? [];
    const next = cur.includes(v) ? cur.filter((x) => x !== v) : [...cur, v];
    setFilters({ ...filters, [k]: next });
  };
  return (
    <aside className="border-r-2 border-ink bg-paper2 px-6 py-6">
      <Group title="Վայր" entries={sortedEntries(facets.location).slice(0, 6)} sel={filters.location ?? []} on={(v) => toggle("location", v)} />
      <Group title="Դերասան" entries={sortedEntries(facets.actors).slice(0, 6)} sel={filters.actors ?? []} on={(v) => toggle("actors", v)} />
      <Group title="Լեզու" entries={sortedEntries(facets.language).slice(0, 4)} sel={filters.language ?? []} on={(v) => toggle("language", v)} />
    </aside>
  );
}
function Group({ title, entries, sel, on }:
  { title: string; entries: [string, number][]; sel: string[]; on: (v: string) => void }) {
  return (
    <div className="mb-6">
      <h4 className="mb-3 text-[11px] font-extrabold uppercase tracking-widest">{title}</h4>
      {entries.map(([name, count]) => (
        <button key={name} onClick={() => on(name)} className="flex w-full items-center gap-2.5 py-2 text-left text-sm">
          <span className={`h-4 w-4 shrink-0 rounded border-2 border-ink ${sel.includes(name) ? "bg-kblue" : ""}`} />
          {name}<span className="ml-auto text-[11px] font-semibold text-muted">{count}</span>
        </button>
      ))}
    </div>
  );
}
