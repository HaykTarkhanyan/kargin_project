import type { Sketch } from "@/lib/types";
import { formatViews, formatDuration } from "@/lib/format";

export default function WatchView({ s }: { s: Sketch }) {
  return (
    <div className="mx-auto grid max-w-5xl grid-cols-1 gap-0 p-6 md:grid-cols-[1.35fr_1fr]">
      <div className="md:border-r-2 md:border-ink md:pr-6">
        <div className="aspect-video overflow-hidden rounded-lg k-border k-shadow">
          <iframe className="h-full w-full" src={`https://www.youtube.com/embed/${s.videoId}`}
            title={s.title} allowFullScreen
            allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture" />
        </div>
        <div className="mt-4 flex flex-wrap gap-2.5">
          <a className="k-border rounded-lg bg-korange px-4 py-2.5 text-sm font-bold" href={s.url} target="_blank" rel="noreferrer">▶ Դիտել YouTube-ում</a>
        </div>
        <dl className="mt-5 grid grid-cols-2 gap-4 border-t-2 border-ink pt-5 text-sm">
          <Meta k="Վայր" v={<span className="rounded-full bg-kblue px-2.5 py-0.5 font-bold text-white">{s.location}</span>} />
          <Meta k="Տևողություն" v={formatDuration(s.durationSec)} />
          <Meta k="Դիտումներ" v={formatViews(s.viewCount)} />
          <Meta k="Վերբեռնված" v={s.uploadDate || "—"} />
          <div className="col-span-2"><Meta k="Դերասաններ" v={s.actors.join(", ") || "—"} /></div>
        </dl>
      </div>
      <div className="bg-paper2 md:pl-0">
        <div className="border-b border-ink/20 px-5 py-4"><h3 className="font-display text-base tracking-wide">ԵՐԿԽՈՍՈՒԹՅՈՒՆ</h3></div>
        <div className="px-5 py-4">
          {s.lines.length === 0
            ? <p className="text-sm text-muted">Դեռ չկա ձեռքով համադրված տեքստ։{s.textCommon ? ` «${s.textCommon}»` : ""}</p>
            : s.lines.map((ln, i) => (
                <div key={i} className="flex gap-3 border-b border-dashed border-ink/15 py-2.5">
                  <span className="shrink-0 cursor-not-allowed rounded border border-ink/25 bg-white px-1.5 text-[11px] font-bold text-muted" title="Ժամանակը՝ շուտով">⏱</span>
                  <span className="text-sm leading-relaxed">{ln}</span>
                </div>
              ))}
        </div>
      </div>
    </div>
  );
}
function Meta({ k, v }: { k: string; v: React.ReactNode }) {
  return <div><dt className="mb-1 text-[10px] font-bold uppercase tracking-widest text-muted">{k}</dt><dd className="font-semibold">{v}</dd></div>;
}
