"use client";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ALL } from "@/lib/data";
import { searchSketches, type Filters, type SortKey } from "@/lib/search";
import { facetCounts } from "@/lib/facets";
import Hero from "./Hero";
import HeroFilters from "./HeroFilters";
import SketchCard from "./SketchCard";
import type { Sketch } from "@/lib/types";

function SketchCardWrapped({ s }: { s: Sketch }) { return <SketchCard sketch={s} />; }

function Experience() {
  const params = useSearchParams();
  const seedLoc = params.get("location");
  const seedActor = params.get("actor");
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<Filters>(() => ({
    ...(seedLoc ? { location: [seedLoc] } : {}),
    ...(seedActor ? { actors: [seedActor] } : {}),
  }));
  const [sort, setSort] = useState<SortKey>("views");
  const facets = useMemo(() => facetCounts(ALL), []);
  const results = useMemo(() => searchSketches(query, ALL, filters, sort), [query, filters, sort]);
  const withDialogue = useMemo(() => ALL.filter((s) => s.text).length, []);
  const totalViews = useMemo(() => ALL.reduce((a, s) => a + (s.viewCount ?? 0), 0), []);
  const totalHours = useMemo(() => Math.round(ALL.reduce((a, s) => a + (s.durationSec ?? 0), 0) / 3600), []);
  const [limit, setLimit] = useState(48);
  useEffect(() => { setLimit(48); }, [query, filters, sort]);

  return (
    <>
      <section className="grid grid-cols-1 gap-6 border-b-2 border-ink px-8 py-12 lg:grid-cols-[1fr_320px]">
        <Hero total={ALL.length} withDialogue={withDialogue} totalViews={totalViews} totalHours={totalHours} onSearch={setQuery} query={query} />
        <HeroFilters facets={facets} filters={filters} setFilters={setFilters} />
      </section>
      <main className="px-8 py-6">
        <div className="mb-6 flex items-center justify-between">
          <div className="font-display text-2xl"><span className="text-kred">{results.length}</span> ԱՐԴՅՈՒՆՔ</div>
          <select value={sort} onChange={(e) => setSort(e.target.value as SortKey)} className="k-border rounded-lg bg-white px-3 py-2 text-sm font-bold">
            <option value="views">Ըստ դիտումների</option><option value="newest">Ամենանորը</option><option value="random">Պատահական</option>
          </select>
        </div>
        {results.length === 0
          ? <div className="k-border rounded-lg bg-card p-10 text-center text-muted">Արդյունք չկա։ Փորձիր այլ բառ կամ մաքրիր զտիչները։</div>
          : <>
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {results.slice(0, limit).map((s) => <SketchCardWrapped key={s.id} s={s} />)}
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
