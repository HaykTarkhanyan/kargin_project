import { notFound } from "next/navigation";
import Link from "next/link";
import { getActorNames, getSketchesForActor, getCoStars } from "@/lib/actors";
import { formatViews } from "@/lib/format";
import SketchGrid from "@/components/SketchGrid";

export function generateStaticParams() {
  // Return raw Armenian strings — Next.js handles URL-encoding in the output path.
  // Do NOT encodeURIComponent here; that would cause double-encoding at build time.
  return getActorNames().map((name) => ({ name }));
}

export default async function ActorPage({ params }: { params: Promise<{ name: string }> }) {
  const { name: rawName } = await params;
  // params.name is the raw URL segment (URL-decoded by Next.js router).
  const actorName = decodeURIComponent(rawName);

  const sketches = getSketchesForActor(actorName);
  if (sketches.length === 0) notFound();

  const sorted = [...sketches].sort((a, b) => (b.viewCount ?? 0) - (a.viewCount ?? 0));

  const totalViews = sketches.reduce((sum, s) => sum + (s.viewCount ?? 0), 0);
  const avgViews = sketches.length > 0 ? Math.round(totalViews / sketches.length) : 0;

  const coStars = getCoStars(actorName, sketches).slice(0, 8);

  const signatureLines = sketches
    .filter((s) => s.textCommon)
    .map((s) => s.textCommon)
    .slice(0, 4);

  return (
    <main className="mx-auto max-w-5xl px-4 py-8 sm:px-7">
      {/* Heading */}
      <div className="mb-6 border-b-2 border-ink pb-5">
        <Link href="/stats" className="mb-3 inline-block text-xs font-bold uppercase tracking-widest text-muted hover:text-ink">
          ← Դերասաններ
        </Link>
        <h1 className="font-display text-5xl sm:text-6xl">{actorName}</h1>
      </div>

      {/* Stats row */}
      <div className="mb-6 grid grid-cols-3 gap-3">
        <div className="k-border k-shadow rounded-lg bg-card p-4">
          <div className="font-display text-3xl text-kred">{sketches.length}</div>
          <div className="text-[10px] font-bold uppercase tracking-widest text-muted">սքեթչ</div>
        </div>
        <div className="k-border k-shadow rounded-lg bg-card p-4">
          <div className="font-display text-3xl text-kblue">{formatViews(totalViews)}</div>
          <div className="text-[10px] font-bold uppercase tracking-widest text-muted">ընդհանուր դիտում</div>
        </div>
        <div className="k-border k-shadow rounded-lg bg-card p-4">
          <div className="font-display text-3xl text-korange">{formatViews(avgViews)}</div>
          <div className="text-[10px] font-bold uppercase tracking-widest text-muted">միջ. դիտ/սքեթչ</div>
        </div>
      </div>

      {/* Co-stars */}
      {coStars.length > 0 && (
        <div className="mb-6">
          <div className="mb-3 font-display text-lg tracking-wide">ՀԱՃԱԽ ԽԱՂՈՒՄ Է</div>
          <div className="flex flex-wrap gap-2">
            {coStars.map(({ name, count }) => (
              <Link
                key={name}
                href={`/actor/${encodeURIComponent(name)}`}
                className="rounded-full border-2 border-ink bg-surface px-3 py-1 text-sm font-bold hover:bg-ink hover:text-paper"
              >
                {name}
                <span className="ml-1.5 text-xs font-normal text-muted">{count}</span>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Signature lines */}
      {signatureLines.length > 0 && (
        <div className="mb-6">
          <div className="mb-3 font-display text-lg tracking-wide">ՍՏՈՐԱԳԻՐ ՏՈՂԵՐ</div>
          <div className="space-y-2">
            {signatureLines.map((line, i) => (
              <div
                key={i}
                className="rounded-md border-2 border-ink border-l-[5px] border-l-korange bg-surface px-3 py-2.5 text-sm font-semibold leading-snug"
              >
                «{line}»
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sketches grid */}
      <div className="mb-3 font-display text-lg tracking-wide">ՍՔԵԹՉԵՐ ({sketches.length})</div>
      <SketchGrid items={sorted} />
    </main>
  );
}
