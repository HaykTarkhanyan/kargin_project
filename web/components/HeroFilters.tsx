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
  const active = (filters.location?.length ?? 0) + (filters.actors?.length ?? 0) + (filters.language?.length ?? 0);
  return (
    // Collapsed by default on phones so the first result is not pushed a whole
    // screen down; always expanded from lg up, where it is the sidebar.
    // Checkbox-and-peer rather than state, so the closed panel is the server
    // markup too and there is no open-then-collapse flash on hydration.
    <div className="k-border k-shadow rounded-lg bg-paper2 px-4 py-1.5 lg:p-4">
      <input id="hero-filters" type="checkbox" className="peer sr-only" defaultChecked={active > 0} />
      <label htmlFor="hero-filters"
        className="flex min-h-11 cursor-pointer select-none items-center justify-between font-display text-base tracking-wide peer-checked:[&_[data-chev]]:rotate-180 lg:pointer-events-none lg:min-h-0">
        <span>ԶՏԻՉՆԵՐ{active > 0 && <span className="ml-2 rounded-full bg-kblue px-2 py-0.5 text-xs text-white">{active}</span>}</span>
        <span data-chev className="text-sm transition-transform lg:hidden" aria-hidden>▾</span>
      </label>
      <div className="hidden peer-checked:block lg:block">
        <Group title="Վայր" entries={sortedEntries(facets.location).slice(0, 6)} sel={filters.location ?? []} on={(v) => toggle("location", v)} />
        <Group title="Դերասան" entries={sortedEntries(facets.actors).slice(0, 6)} sel={filters.actors ?? []} on={(v) => toggle("actors", v)} />
        <Group title="Լեզու" entries={sortedEntries(facets.language).slice(0, 4)} sel={filters.language ?? []} on={(v) => toggle("language", v)} />
      </div>
    </div>
  );
}
function Group({ title, entries, sel, on }:
  { title: string; entries: [string, number][]; sel: string[]; on: (v: string) => void }) {
  return (
    <details className="border-t border-ink/15" open={sel.length > 0}>
      <summary className="flex min-h-11 cursor-pointer items-center text-[11px] font-extrabold uppercase tracking-widest">
        {title}{sel.length ? ` (${sel.length})` : ""}
      </summary>
      <div className="mb-2 flex flex-wrap gap-1.5">
        {entries.map(([name, count]) => (
          <button key={name} onClick={() => on(name)} className={`min-h-9 rounded-full border-2 border-ink px-3 py-1.5 text-xs font-semibold ${sel.includes(name) ? "bg-kblue text-white" : "bg-surface"}`}>
            {name} <span className="opacity-60">{count}</span>
          </button>
        ))}
      </div>
    </details>
  );
}
