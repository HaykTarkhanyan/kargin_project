import Link from "next/link";
import type { Sketch } from "@/lib/types";
import { formatViews, formatDuration } from "@/lib/format";
import { related } from "@/lib/related";
import { ALL } from "@/lib/data";
import CopyButton from "./CopyButton";
import RelatedList from "./RelatedList";

export default function WatchView({ s }: { s: Sketch }) {
  return (
    <div className="mx-auto grid max-w-5xl grid-cols-1 gap-0 p-4 sm:p-6 md:grid-cols-[1.35fr_1fr]">
      <div className="md:border-r-2 md:border-ink md:pr-6">
        <div className="aspect-video overflow-hidden rounded-lg k-border k-shadow">
          <iframe className="h-full w-full" src={`https://www.youtube.com/embed/${s.videoId}`}
            title={s.title} allowFullScreen
            allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture" />
        </div>
        <div className="mt-4 flex flex-wrap gap-2.5">
          <a className="k-border rounded-lg bg-korange px-4 py-2.5 text-sm font-bold" href={s.url} target="_blank" rel="noreferrer">▶ Դիտել YouTube-ում</a>
          <CopyButton label="🔗 Պատճենել հղումը" getHref />
          {s.textCommon && <CopyButton label="Պատճենել տողը" value={s.textCommon} />}
        </div>
        <dl className="mt-5 grid grid-cols-2 gap-4 border-t-2 border-ink pt-5 text-sm">
          <Meta k="Վայր" v={<span className="rounded-full bg-kblue px-2.5 py-0.5 font-bold text-white">{s.location}</span>} />
          <Meta k="Տևողություն" v={formatDuration(s.durationSec)} />
          <Meta k="Դիտումներ" v={formatViews(s.viewCount)} />
          <Meta k="Վերբեռնված" v={s.uploadDate || "—"} />
          <div className="col-span-2"><Meta k="Դերասաններ" v={s.actors.join(", ") || "—"} /></div>
        </dl>
      </div>
      <div className="bg-paper2 px-5 py-5">
        {s.textCommon && (
          <div className="mb-3 rounded-md border-2 border-ink border-l-[5px] border-l-korange bg-white px-3 py-2.5">
            <div className="mb-1 text-[10px] font-extrabold uppercase tracking-wider text-kred">★ Հանրահայտ տողը</div>
            <div className="text-sm font-semibold leading-snug">«{s.textCommon}»</div>
          </div>
        )}
        <div className="mb-4 flex flex-wrap gap-2">
          {s.actors.map((a) => (
            <Link key={a} href={`/find-my-name?name=${encodeURIComponent(a)}`} className="rounded-full border-2 border-ink bg-white px-3 py-1 text-xs font-bold hover:bg-ink hover:text-paper">{a}</Link>
          ))}
          {s.location !== "Այլ" && (
            <Link href={`/?location=${encodeURIComponent(s.location)}`} className="rounded-full border-2 border-kblue bg-kblue px-3 py-1 text-xs font-bold text-white">📍 {s.location}</Link>
          )}
        </div>
        <div className="mb-2 border-t-2 border-ink pt-3 font-display text-base tracking-wide">ՆՄԱՆԱՏԻՊ</div>
        <RelatedList items={related(s, ALL, 6)} />
      </div>
    </div>
  );
}
function Meta({ k, v }: { k: string; v: React.ReactNode }) {
  return <div><dt className="mb-1 text-[10px] font-bold uppercase tracking-widest text-muted">{k}</dt><dd className="font-semibold">{v}</dd></div>;
}
