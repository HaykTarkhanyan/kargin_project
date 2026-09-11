"use client";
import { useMemo, useState } from "react";
import Link from "next/link";
import { ALL } from "@/lib/data";
import { normalize } from "@/lib/normalize";
import { formatDuration, formatViews } from "@/lib/format";
import type { Sketch } from "@/lib/types";

type SortKey = "seq" | "title" | "location" | "durationSec" | "viewCount" | "uploadDate" | "songs" | "chars";
type Dir = "asc" | "desc";

const PAGE = 100;

/** Everything the free-text box looks at, built once per sketch. */
const haystack = new WeakMap<Sketch, string>();
function rowText(s: Sketch): string {
  let v = haystack.get(s);
  if (v === undefined) {
    v = normalize([
      s.title, s.text, s.textCommon, s.actorsRaw, s.rolesNames, s.location,
      s.visual?.synopsis ?? "", s.visual?.locationFine ?? "",
      (s.songs ?? []).map((g) => `${g.artist} ${g.title}`).join(" "),
    ].join(" "));
    haystack.set(s, v);
  }
  return v;
}

/** null for "this row has no value", so it can be sorted to the end either way. */
const value = (s: Sketch, k: SortKey): string | number | null => {
  switch (k) {
    case "songs": return s.songs?.length ?? 0;
    case "chars": return s.text.length;
    case "seq": return s.seq;                 // 104 sketches have none
    case "durationSec": return s.durationSec;
    case "viewCount": return s.viewCount;
    case "title": return s.title;
    case "location": return s.location;
    case "uploadDate": return s.uploadDate || null;
  }
};

const COLUMNS: { key: SortKey; label: string; width: string; numeric?: boolean }[] = [
  { key: "seq", label: "#", width: "56px", numeric: true },
  { key: "title", label: "Վերնագիր", width: "28%" },
  { key: "location", label: "Վայր", width: "110px" },
  { key: "durationSec", label: "Տևող.", width: "76px", numeric: true },
  { key: "viewCount", label: "Դիտում", width: "88px", numeric: true },
  { key: "uploadDate", label: "Ամսաթիվ", width: "108px" },
  { key: "chars", label: "Տեքստ", width: "78px", numeric: true },
  { key: "songs", label: "🎵", width: "56px", numeric: true },
];

function download(name: string, body: string, mime: string) {
  const url = URL.createObjectURL(new Blob([body], { type: `${mime};charset=utf-8` }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

/** RFC4180 quoting — the dialogue is full of commas, quotes and newlines. */
const csvCell = (v: unknown) => `"${String(v ?? "").replace(/"/g, '""')}"`;

export default function DataTable() {
  const [q, setQ] = useState("");
  const [loc, setLoc] = useState("");
  const [actor, setActor] = useState("");
  const [only, setOnly] = useState<Record<string, boolean>>({});
  // Views, not seq: every sketch has a view count, only 598 of 702 have a number.
  const [sort, setSort] = useState<SortKey>("viewCount");
  const [dir, setDir] = useState<Dir>("desc");
  const [limit, setLimit] = useState(PAGE);

  const locations = useMemo(() => [...new Set(ALL.map((s) => s.location))].sort(), []);
  const actors = useMemo(() => [...new Set(ALL.flatMap((s) => s.actors))].sort(), []);

  const rows = useMemo(() => {
    const needle = normalize(q);
    const out = ALL.filter((s) => {
      if (needle && !rowText(s).includes(needle)) return false;
      if (loc && s.location !== loc) return false;
      if (actor && !s.actors.includes(actor)) return false;
      if (only.text && !s.text) return false;
      if (only.transcript && !s.transcript) return false;
      if (only.songs && !s.songs?.length) return false;
      if (only.visual && !s.visual) return false;
      return true;
    });
    const sign = dir === "asc" ? 1 : -1;
    return out.sort((a, b) => {
      const x = value(a, sort), y = value(b, sort);
      // Blanks last in both directions — 104 sketches have no sequence number,
      // and sorting them as zero buried the real rows under a wall of dashes.
      if (x === null || y === null) return x === y ? 0 : x === null ? 1 : -1;
      if (typeof x === "number" && typeof y === "number") return (x - y) * sign;
      return String(x).localeCompare(String(y), "hy") * sign;
    });
  }, [q, loc, actor, only, sort, dir]);

  const toggleSort = (k: SortKey) => {
    if (k === sort) setDir(dir === "asc" ? "desc" : "asc");
    else { setSort(k); setDir(k === "viewCount" || k === "chars" || k === "songs" ? "desc" : "asc"); }
    setLimit(PAGE);
  };

  const exportRows = () => rows.map((s) => ({
    id: s.id, seq: s.seq, title: s.title, url: s.url, location: s.location,
    actors: s.actors.join("|"), roles: s.rolesNames, languages: s.languages.join("|"),
    durationSec: s.durationSec, viewCount: s.viewCount, uploadDate: s.uploadDate,
    textCommon: s.textCommon, text: s.text,
    transcript: s.transcript?.text ?? "", transcriptSource: s.transcript?.source ?? "",
    visualSynopsis: s.visual?.synopsis ?? "", visualLocation: s.visual?.locationFine ?? "",
    songs: (s.songs ?? []).map((g) => `${g.artist} — ${g.title}`).join("|"),
  }));

  const toCsv = () => {
    const data = exportRows();
    const head = Object.keys(data[0] ?? { id: "" });
    return [head.join(","), ...data.map((r) => head.map((k) => csvCell((r as Record<string, unknown>)[k])).join(","))].join("\r\n");
  };

  const chip = (key: string, label: string) => (
    <button key={key} onClick={() => { setOnly({ ...only, [key]: !only[key] }); setLimit(PAGE); }}
      className={`min-h-9 rounded-full border-2 border-ink px-3 text-xs font-semibold ${only[key] ? "bg-kblue text-white" : "bg-surface"}`}>
      {label}
    </button>
  );

  return (
    <>
      <div className="k-border k-shadow mb-5 rounded-lg bg-paper2 p-4">
        <input value={q} onChange={(e) => { setQ(e.target.value); setLimit(PAGE); }}
          type="search" placeholder="Զտիր ըստ տեքստի, դերասանի, վայրի…"
          // 16px minimum or iOS Safari zooms the page on focus.
          className="k-border w-full rounded-lg bg-surface px-4 py-3 text-[16px] outline-none" />
        <div className="mt-3 flex flex-wrap gap-2">
          <select value={loc} onChange={(e) => { setLoc(e.target.value); setLimit(PAGE); }}
            className="k-border min-h-9 rounded-lg bg-surface px-2 text-sm font-semibold">
            <option value="">Բոլոր վայրերը</option>
            {locations.map((l) => <option key={l} value={l}>{l}</option>)}
          </select>
          <select value={actor} onChange={(e) => { setActor(e.target.value); setLimit(PAGE); }}
            className="k-border min-h-9 rounded-lg bg-surface px-2 text-sm font-semibold">
            <option value="">Բոլոր դերասանները</option>
            {actors.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
          {chip("text", "✍️ համադրված տեքստ")}
          {chip("transcript", "🤖 վերծանում")}
          {chip("songs", "🎵 երաժշտություն")}
          {chip("visual", "🎬 տեսարան")}
        </div>
      </div>

      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="font-display text-xl">
          <span className="text-kred">{rows.length}</span> / {ALL.length} ՏՈՂ
        </div>
        <div className="flex gap-2">
          <button onClick={() => download("kargin-filtered.csv", toCsv(), "text/csv")}
            className="k-border min-h-11 rounded-lg bg-surface px-4 text-sm font-bold">CSV</button>
          <button onClick={() => download("kargin-filtered.json", JSON.stringify(exportRows(), null, 2), "application/json")}
            className="k-border min-h-11 rounded-lg bg-surface px-4 text-sm font-bold">JSON</button>
        </div>
      </div>

      {/* The table is wider than a phone; it scrolls inside its own box, and
          overscroll-x-contain stops that swipe turning into a back-navigation. */}
      <div className="k-border overflow-x-auto overscroll-x-contain rounded-lg bg-card">
        <table className="w-full table-fixed border-collapse text-sm" style={{ minWidth: "760px" }}>
          <colgroup>{COLUMNS.map((c) => <col key={c.key} style={{ width: c.width }} />)}</colgroup>
          <thead>
            <tr className="border-b-2 border-ink bg-paper2">
              {COLUMNS.map((c) => (
                <th key={c.key} onClick={() => toggleSort(c.key)}
                  className={`cursor-pointer select-none px-2 py-2 text-[11px] font-extrabold uppercase tracking-wider ${c.numeric ? "text-right" : "text-left"} hover:text-kred`}>
                  {c.label}{sort === c.key ? (dir === "asc" ? " ▲" : " ▼") : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, limit).map((s) => (
              <tr key={s.id} className="border-b border-ink/12 align-top hover:bg-paper2/60">
                <td className="px-2 py-2 text-right tabular-nums text-muted">{s.seq ?? "—"}</td>
                <td className="px-2 py-2">
                  <Link href={`/sketch/${s.id}`} className="font-semibold underline-offset-2 hover:underline">
                    {s.title}
                  </Link>
                  {s.textCommon && <div className="truncate text-xs text-muted">«{s.textCommon}»</div>}
                </td>
                <td className="px-2 py-2">{s.location}</td>
                <td className="px-2 py-2 text-right tabular-nums">{formatDuration(s.durationSec)}</td>
                <td className="px-2 py-2 text-right tabular-nums">{formatViews(s.viewCount)}</td>
                <td className="px-2 py-2 tabular-nums text-muted">{s.uploadDate || "—"}</td>
                <td className="px-2 py-2 text-right tabular-nums text-muted">{s.text.length || "—"}</td>
                <td className="px-2 py-2 text-right tabular-nums text-muted">{s.songs?.length || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {rows.length === 0 && <p className="mt-5 text-center text-muted">Այս զտիչներով տող չկա։</p>}
      {rows.length > limit && (
        <div className="mt-6 flex justify-center">
          <button onClick={() => setLimit((l) => l + PAGE)}
            className="k-border k-shadow min-h-11 rounded-lg bg-korange px-6 font-bold text-[#1A1410]">
            Ցույց տալ ևս ({rows.length - limit})
          </button>
        </div>
      )}
    </>
  );
}
