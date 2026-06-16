import { Fragment } from "react";
import Link from "next/link";
import { formatViews } from "@/lib/format";

const FLAG = ["#D90012", "#0033A0", "#F2A800"];

export function Card({ title, note, children, full }: { title: string; note?: string; children: React.ReactNode; full?: boolean }) {
  return (
    <div className={`k-border k-shadow rounded-xl bg-card p-4 ${full ? "md:col-span-2" : ""}`}>
      <h3 className="font-display text-lg">{title}</h3>{note && <p className="mb-3 text-xs text-muted">{note}</p>}
      {children}
    </div>
  );
}

export function BarList({ rows, color = "#D90012", fmt = String, hrefFor }:
  { rows: { label: string; value: number }[]; color?: string; fmt?: (n: number) => string; hrefFor?: (l: string) => string }) {
  const max = Math.max(...rows.map((r) => r.value), 1);
  return (
    <div role="img" aria-label="բարային գծապատկեր">
      {rows.map((r) => {
        const lbl = hrefFor ? <Link href={hrefFor(r.label)} className="hover:underline">{r.label}</Link> : r.label;
        return (
          <div key={r.label} className="my-2 grid grid-cols-[84px_1fr_52px] items-center gap-2">
            <div className="truncate text-right text-xs font-bold">{lbl}</div>
            <div className="h-[22px] overflow-hidden rounded border-2 border-ink bg-white"><div className="h-full" style={{ width: `${(r.value / max) * 100}%`, background: color }} /></div>
            <div className="text-right text-xs font-extrabold">{fmt(r.value)}</div>
          </div>
        );
      })}
    </div>
  );
}

export function Scatter({ points }: { points: { name: string; x: number; y: number; n: number }[] }) {
  const maxX = Math.max(...points.map((p) => p.x)), maxY = Math.max(...points.map((p) => p.y));
  const px = (x: number) => 40 + (x / maxX) * 270, py = (y: number) => 185 - (y / maxY) * 165;
  return (
    <svg viewBox="0 0 340 210" role="img" aria-label="հազվադեպ հյուրերն ունեն ամենաբարձր միջին դիտումը">
      <line x1="40" y1="185" x2="320" y2="185" stroke="#1A1410" strokeWidth="1.5" /><line x1="40" y1="185" x2="40" y2="15" stroke="#1A1410" strokeWidth="1.5" />
      {points.map((p, i) => (
        <g key={p.name}>
          <circle cx={px(p.x)} cy={py(p.y)} r={4 + Math.sqrt(p.n)} fill={`${FLAG[i % 3]}66`} stroke="#1A1410" />
          <text x={px(p.x)} y={py(p.y) + (i % 2 ? 17 : -10)} textAnchor="middle" className="fill-ink" style={{ font: "800 10px sans-serif" }}>{p.name}</text>
        </g>
      ))}
    </svg>
  );
}

export function Heatmap({ actors, matrix }: { actors: string[]; matrix: number[][] }) {
  const max = Math.max(...matrix.flat(), 1);
  return (
    <div role="img" aria-label="դերասանների համատեղ հանդես գալը" className="grid gap-[3px] text-[10px]" style={{ gridTemplateColumns: `auto repeat(${actors.length}, 1fr)`, minWidth: `${actors.length * 36 + 40}px` }}>
      <div />{actors.map((a) => <div key={a} className="text-center font-bold">{a.slice(0, 4)}</div>)}
      {actors.map((row, i) => (
        <Fragment key={row}>
          <div className="flex items-center justify-end pr-1 font-bold">{row.slice(0, 5)}</div>
          {actors.map((_, j) => (
            <div key={i + "-" + j} className="flex aspect-square items-center justify-center rounded border-[1.5px] border-ink font-extrabold"
              style={{ background: i === j ? "repeating-linear-gradient(45deg,#eee,#eee 3px,#fff 3px,#fff 6px)" : `rgba(242,168,0,${matrix[i][j] / max})` }}>
              {i === j ? "" : matrix[i][j] || ""}
            </div>
          ))}
        </Fragment>
      ))}
    </div>
  );
}

export function TrendLine({ points }: { points: { label: string; value: number }[] }) {
  const max = Math.max(...points.map((p) => p.value), 1);
  const xs = points.map((_, i) => 40 + (i / (points.length - 1)) * 260);
  const ys = points.map((p) => 145 - (p.value / max) * 125);
  const path = xs.map((x, i) => `${x},${ys[i]}`).join(" ");
  return (
    <svg viewBox="0 0 340 170" role="img" aria-label="ավելի երկար սքեթչներն ավելի շատ դիտում ունեն">
      <line x1="40" y1="145" x2="320" y2="145" stroke="#1A1410" strokeWidth="1.5" />
      <polyline points={path} fill="none" stroke="#D90012" strokeWidth="3" />
      {points.map((p, i) => (<g key={p.label}><circle cx={xs[i]} cy={ys[i]} r="4" fill="#1A1410" /><text x={xs[i]} y="160" textAnchor="middle" className="fill-muted" style={{ font: "600 9px sans-serif" }}>{p.label}</text><text x={xs[i]} y={ys[i] - 7} textAnchor="middle" style={{ font: "800 9px sans-serif" }}>{formatViews(p.value)}</text></g>))}
    </svg>
  );
}

export function WordField({ words }: { words: { w: string; n: number }[] }) {
  const max = Math.max(...words.map((x) => x.n), 1);
  return (
    <div className="flex flex-wrap items-center gap-1.5" role="img" aria-label="ամենահաճախ բառերը">
      {words.map((x, i) => (<span key={x.w} className="rounded-md border-2 border-ink bg-white px-2 py-0.5 font-extrabold" style={{ fontSize: 12 + (x.n / max) * 16, color: FLAG[i % 3] }}>{x.w}</span>))}
    </div>
  );
}

export function StackedBar({ parts }: { parts: { label: string; value: number; color: string }[] }) {
  const total = parts.reduce((a, p) => a + p.value, 0) || 1;
  return (
    <div>
      <div className="flex h-8 overflow-hidden rounded border-2 border-ink">
        {parts.map((p) => <div key={p.label} style={{ width: `${(p.value / total) * 100}%`, background: p.color }} />)}
      </div>
      <div className="mt-2 flex flex-wrap gap-3 text-xs font-semibold">
        {parts.map((p) => <span key={p.label}><span className="inline-block h-3 w-3 rounded-sm border border-ink align-middle" style={{ background: p.color }} /> {p.label} ({p.value})</span>)}
      </div>
    </div>
  );
}
