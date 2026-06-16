"use client";
import { useMemo, useState } from "react";
import { ALL } from "@/lib/data";
import { searchSketches, type Filters, type SortKey } from "@/lib/search";
import { facetCounts } from "@/lib/facets";
import Hero from "./Hero";
import FilterRail from "./FilterRail";
import SketchGrid from "./SketchGrid";

export default function SearchExperience() {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<Filters>({});
  const [sort, setSort] = useState<SortKey>("views");
  const facets = useMemo(() => facetCounts(ALL), []);
  const results = useMemo(() => searchSketches(query, ALL, filters, sort), [query, filters, sort]);
  const withDialogue = useMemo(() => ALL.filter((s) => s.text).length, []);
  const totalViews = useMemo(() => ALL.reduce((a, s) => a + (s.viewCount ?? 0), 0), []);
  const totalHours = useMemo(() => Math.round(ALL.reduce((a, s) => a + (s.durationSec ?? 0), 0) / 3600), []);

  return (
    <>
      <Hero total={ALL.length} withDialogue={withDialogue} totalViews={totalViews} totalHours={totalHours} onSearch={setQuery} query={query} />
      <div className="grid grid-cols-1 md:grid-cols-[248px_1fr]">
        <FilterRail facets={facets} filters={filters} setFilters={setFilters} />
        <main className="px-8 py-6">
          <div className="mb-6 flex items-center justify-between">
            <div className="font-display text-2xl"><span className="text-kred">{results.length}</span> ԱՐԴՅՈՒՆՔ</div>
            <select value={sort} onChange={(e) => setSort(e.target.value as SortKey)} className="k-border rounded-lg bg-white px-3 py-2 text-sm font-bold">
              <option value="views">Ըստ դիտումների</option>
              <option value="newest">Ամենանորը</option>
              <option value="random">Պատահական</option>
            </select>
          </div>
          {results.length === 0
            ? <div className="k-border rounded-lg bg-card p-10 text-center text-muted">Արդյունք չկա։ Փորձիր այլ բառ կամ մաքրիր զտիչները։</div>
            : <SketchGrid items={results} />}
        </main>
      </div>
    </>
  );
}
