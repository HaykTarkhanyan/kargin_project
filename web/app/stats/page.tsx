import { STATS } from "@/lib/stats-data";
import { Card, BarList, Scatter, Heatmap, TrendLine, WordField, StackedBar } from "@/components/stats/Charts";
import { formatViews } from "@/lib/format";

export default function StatsPage() {
  const s = STATS;
  return (
    <main className="mx-auto max-w-5xl px-4 py-8 sm:px-7">
      <h1 className="mb-4 font-display text-4xl">Վիճակագրություն</h1>

      <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-5">
        {[["702", "սքեթչ"], [`${s.totals.hours}ժ`, "ընդհանուր"], [formatViews(s.totals.views), "դիտում"], [`${s.totals.actors}`, "դերասան"], ["10", "ամիս"]].map(([n, l], i) => (
          <div key={l} className="k-border k-shadow rounded-lg bg-card p-3"><div className="font-display text-2xl" style={{ color: ["#D90012", "#0033A0", "#F2A800", "#D90012", "#0033A0"][i] }}>{n}</div><div className="text-[10px] font-bold uppercase tracking-widest text-muted">{l}</div></div>
        ))}
      </div>

      <div className="mb-6 rounded-lg bg-ink px-5 py-4 text-base font-bold text-paper">🎭 Հայկո֊ն ու Մկո֊ն՝ սքեթչների <span className="text-korange">~76%</span>-ում · ամենաերկարը՝ <span className="text-korange">{s.extremes.longestMin}ր</span> · ամենադիտվածը՝ <span className="text-korange">{formatViews(s.topViewed[0].views)}</span></div>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        <Card title="Աստղային ուժ" note="հազվադեպ հյուրերն ունեն ամենաբարձր միջին դիտումը (պղպջակ = ներկայություն)">
          <Scatter points={s.actorsAvgViews.map((a) => ({ name: a.name, x: a.n, y: a.avgViews, n: a.n }))} />
        </Card>
        <Card title="Ո՞վ ում հետ" note="միասին քանի՞ սքեթչում"><div className="overflow-x-auto"><Heatmap actors={s.coOccurrence.actors} matrix={s.coOccurrence.matrix} /></div></Card>
        <Card title="Երկարությունն ու դիտումները" note="միջին դիտում ըստ տևողության"><TrendLine points={s.durationBuckets.map((d) => ({ label: d.bucket, value: d.avgViews }))} /></Card>
        <Card title="Ստորագիր արտահայտություններ" note="ամենահաճախ զույգ բառերը"><BarList rows={s.topPhrases.map((p) => ({ label: p.p, value: p.n }))} color="#0033A0" /></Card>
        <Card title="Դերասաններ" note="քանի՞ սքեթչում"><BarList rows={s.actorsByCount.map((a) => ({ label: a.name, value: a.n }))} hrefFor={(l) => `/actor/${encodeURIComponent(l)}`} /></Card>
        <Card title="Վայր" note="«Այլ» = դեռ չդասակարգված"><BarList rows={s.locationByCount.map((l) => ({ label: l.loc, value: l.n }))} color="#0033A0" hrefFor={(l) => l === "Այլ" ? "#" : `/?location=${encodeURIComponent(l)}`} /></Card>
        <Card title="Ամենադիտված 5-ը"><BarList rows={s.topViewed.map((t) => ({ label: t.seq ? `սքեթչ ${t.seq}` : t.title.slice(0, 12), value: t.views }))} fmt={formatViews} /></Card>
        <Card title="Դիտումների բաշխում"><BarList rows={s.viewsHistogram.map((h) => ({ label: h.bucket, value: h.n }))} color="#F2A800" /></Card>
        <Card title="Կազմ"><StackedBar parts={[{ label: "Հայկո+Մկո", value: s.composition.duo, color: "#D90012" }, { label: "անսամբլ", value: s.composition.ensemble, color: "#0033A0" }, { label: "մենակ", value: s.composition.solo, color: "#F2A800" }, { label: "չդասակարգված", value: s.composition.uncurated, color: "#8a7c64" }]} /></Card>
        <Card title="Կարգինի բառապաշարը" note="(ստորագիր արտահայտություններն ավելի հետաքրքիր են վերևում)"><WordField words={s.topWords} /></Card>
        <Card title="Միջին դիտում ըստ վայրի" note="Խանութը գերակատարում է (առանց «Այլ»-ի)"><BarList rows={s.locationAvgViews.map((l) => ({ label: l.loc, value: l.avgViews }))} fmt={formatViews} color="#0033A0" /></Card>
        <Card title="Դիտումները շարքի ընթացքում" note="միջին դիտում ըստ սքեթչի համարի (598-ը՝ համարով)"><TrendLine points={s.viewsBySeq.map((b) => ({ label: b.label.split("-")[0], value: b.avgViews }))} /></Card>
      </div>
    </main>
  );
}
