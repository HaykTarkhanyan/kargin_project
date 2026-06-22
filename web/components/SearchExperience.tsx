"use client";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ALL } from "@/lib/data";
import { searchSketches, type Filters, type SortKey } from "@/lib/search";
import { facetCounts } from "@/lib/facets";
import { logEvent } from "@/lib/log";
import Hero from "./Hero";
import HeroFilters from "./HeroFilters";
import SketchCard from "./SketchCard";

function Experience() {
  const params = useSearchParams();
  const seedLoc = params.get("location");
  const seedActor = params.get("actor");
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(query), 180); // search after typing pauses
    return () => clearTimeout(t);
  }, [query]);
  const [filters, setFilters] = useState<Filters>(() => ({
    ...(seedLoc ? { location: [seedLoc] } : {}),
    ...(seedActor ? { actors: [seedActor] } : {}),
  }));
  const [sort, setSort] = useState<SortKey>("views");
  const facets = useMemo(() => facetCounts(ALL), []);
  const results = useMemo(() => searchSketches(debouncedQuery, ALL, filters, sort), [debouncedQuery, filters, sort]);
  const withDialogue = useMemo(() => ALL.filter((s) => s.text).length, []);
  const totalViews = useMemo(() => ALL.reduce((a, s) => a + (s.viewCount ?? 0), 0), []);
  const totalHours = useMemo(() => Math.round(ALL.reduce((a, s) => a + (s.durationSec ?? 0), 0) / 3600), []);
  const [limit, setLimit] = useState(48);
  // Reset pagination when the result set changes (input-derived UI state).
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { setLimit(48); }, [debouncedQuery, filters, sort]);

  // Usage logging (no-op unless the build sets NEXT_PUBLIC_LOG_ENDPOINT).
  // Keyed on the debounced query so `results` is the value computed for this exact
  // search; logEvent itself batches, so no extra timer is needed here.
  useEffect(() => {
    const q = debouncedQuery.trim();
    if (q) logEvent("search", { query: q, mode: "exact", resultCount: results.length, source: "home" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQuery]);
  useEffect(() => {
    const active = (filters.location?.length ?? 0) + (filters.actors?.length ?? 0) + (filters.language?.length ?? 0) + (filters.duration ? 1 : 0);
    if (active > 0) logEvent("filter", { filters, resultCount: results.length, source: "home" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  return (
    <>
      <section className="grid grid-cols-1 gap-6 border-b-2 border-ink px-4 py-8 sm:px-8 sm:py-12 lg:grid-cols-[1fr_320px]">
        <Hero total={ALL.length} withDialogue={withDialogue} totalViews={totalViews} totalHours={totalHours} onSearch={setQuery} query={query} />
        <HeroFilters facets={facets} filters={filters} setFilters={setFilters} />
      </section>
      <main className="px-4 py-6 sm:px-8">
        <div className="mb-6 flex items-center justify-between">
          <div className="font-display text-2xl"><span className="text-kred">{results.length}</span> ԱՐԴՅՈՒՆՔ</div>
          <select value={sort} onChange={(e) => setSort(e.target.value as SortKey)} className="k-border rounded-lg bg-surface px-3 py-2 text-sm font-bold">
            <option value="views">Ըստ դիտումների</option><option value="newest">Ամենանորը</option><option value="random">Պատահական</option>
          </select>
        </div>
        {results.length === 0
          ? <div className="k-border rounded-lg bg-card p-10 text-center text-muted">Արդյունք չկա։ Փորձիր այլ բառ կամ մաքրիր զտիչները։</div>
          : <>
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {results.slice(0, limit).map((s) => <SketchCard key={s.id} sketch={s} />)}
              </div>
              {results.length > limit && (
                <div className="mt-8 flex justify-center">
                  <button onClick={() => setLimit((l) => l + 48)} className="k-border k-shadow rounded-lg bg-korange px-6 py-3 font-bold">Բեռնել ևս ({results.length - limit})</button>
                </div>)}
            </>}
      </main>
    </>
  );
}

export default function SearchExperience() {
  return <Suspense fallback={<div className="p-10 text-muted">Բեռնում…</div>}><Experience /></Suspense>;
}
