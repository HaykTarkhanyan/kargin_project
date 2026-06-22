"use client";
import { Suspense, useMemo, useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { ALL } from "@/lib/data";
import { STATS } from "@/lib/stats-data";
import { findByName } from "@/lib/findName";
import { formatViews } from "@/lib/format";
import { logEvent } from "@/lib/log";

const CAST = ["Հայկո", "Մկո", "Աշոտ", "Հասմիկ", "Անդո", "Ռաֆո"];

function Finder() {
  const seed = useSearchParams().get("name") ?? "";
  const [name, setName] = useState(seed);
  const [dq, setDq] = useState(seed);
  // Sync the input to the ?name= URL param on client-side navigation.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { setName(seed); }, [seed]);
  useEffect(() => {
    const t = setTimeout(() => setDq(name), 180); // search after typing pauses (matches home search)
    return () => clearTimeout(t);
  }, [name]);
  const chips = useMemo(() => [...CAST, ...STATS.nameSuggestions.map((x) => x.name)], []);
  const results = useMemo(() => (dq.trim() ? findByName(dq, ALL) : []), [dq]);

  useEffect(() => {
    if (dq.trim()) logEvent("findname", { query: dq, resultCount: results.length, source: "findname" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dq]);

  return (
    <main>
      <section className="border-b-2 border-ink px-4 py-8 text-center sm:px-7 sm:py-10">
        <h1 className="font-display text-4xl sm:text-5xl">Գտի՛ր <span className="text-kred">քո անունը</span></h1>
        <p className="mx-auto mt-3 max-w-[46ch] text-muted">Որ սքեթչներում է հնչում քո անունը — դերասանի, դերի կամ երկխոսության մեջ։</p>
        <div className="mx-auto mt-5 flex max-w-md k-border k-shadow rounded-lg bg-surface">
          <span className="flex items-center pl-4 pr-1 text-lg">🔎</span>
          <input value={name} onChange={(e) => setName(e.target.value)} autoFocus className="w-full bg-transparent px-2 py-3.5 text-lg font-bold outline-none" placeholder="անուն…" />
        </div>
        <div className="mx-auto mt-4 flex max-w-xl flex-wrap justify-center gap-2">
          {chips.map((c) => (
            <button key={c} onClick={() => setName(c)} className={`rounded-full border-2 border-ink px-3 py-1.5 text-sm font-bold ${name === c ? "bg-kred text-white" : "bg-surface"}`}>{c}</button>
          ))}
        </div>
      </section>

      <div className="mx-auto max-w-5xl px-4 py-6 sm:px-7">
        {name.trim() && (
          <div className="mb-4 font-display text-2xl"><span className="text-kred">«{name}»</span> — {results.length} սքեթչ</div>
        )}
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {results.map(({ sketch: s, kind, snippet }) => (
            <Link key={s.id} href={`/sketch/${s.id}`} className="k-border k-shadow overflow-hidden rounded-xl bg-card hover:opacity-95">
              <div className="relative aspect-video border-b-2 border-ink bg-cover bg-center" style={{ backgroundImage: `url(${s.thumbnail})` }}>
                <span className={`absolute left-2 top-2 rounded-full border-[1.5px] border-ink px-2.5 py-0.5 text-[10.5px] font-extrabold ${kind === "actor" ? "bg-korange" : "bg-surface"}`}>{kind === "actor" ? "🎭 Դերասան" : "💬 Հիշատակվում"}</span>
              </div>
              <div className="p-3.5">
                <div className="mb-1.5 text-sm font-bold">{s.title}</div>
                {kind === "mention" && snippet && <div className="mb-2 border-l-[3px] border-korange pl-2.5 text-xs opacity-80">«{snippet.slice(0, 90)}»</div>}
                <div className="text-[11px] font-semibold text-muted">{s.location} · {formatViews(s.viewCount)} դիտում</div>
              </div>
            </Link>
          ))}
        </div>
        {name.trim() && results.length === 0 && <p className="text-muted">Չգտնվեց։ Փորձիր մեկ այլ անուն։</p>}
      </div>
    </main>
  );
}

export default function FindMyNamePage() {
  return <Suspense fallback={<div className="p-10 text-muted">Բեռնում…</div>}><Finder /></Suspense>;
}