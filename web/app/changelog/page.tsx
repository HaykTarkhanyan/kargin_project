import { CHANGELOG, type ChangelogItem } from "@/lib/changelog";
import { ALL } from "@/lib/data";

// Server component: ALL is read at build time, so the figures below are real
// and never drift, and none of the dataset reaches the client bundle.
const COUNTS = {
  sketches: ALL.length,
  withText: ALL.filter((s) => s.text).length,
  sketchesWithSongs: ALL.filter((s) => s.songs?.length).length,
  songs: ALL.reduce((n, s) => n + (s.songs?.length ?? 0), 0),
};

const SUFFIX: Record<NonNullable<ChangelogItem["count"]>, (n: number) => string> = {
  sketchesWithSongs: (n) => `${n} սքեթչում`,
  songs: (n) => `${n} երգ`,
  sketches: (n) => `${n} սքեթչ`,
  withText: (n) => `${n} սքեթչում`,
};

export default function Changelog() {
  return (
    <main className="mx-auto max-w-2xl px-4 py-10 sm:px-8 sm:py-14">
      <h1 className="font-display text-4xl sm:text-5xl">Նորություններ</h1>
      <p className="mt-4 leading-relaxed opacity-75">
        Ինչ է փոխվել կայքում։ Ամենանորը՝ վերևում։
      </p>

      <ol className="mt-10 space-y-10">
        {CHANGELOG.map((entry, i) => (
          <li key={`${entry.date}-${i}`} className="border-l-[3px] border-ink/25 pl-5">
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <h2 className="font-display text-2xl">{entry.title}</h2>
              <time dateTime={entry.date} className="text-xs font-bold uppercase tracking-widest text-muted">
                {entry.date}
              </time>
            </div>
            <ul className="mt-3 space-y-2.5">
              {entry.items.map((item, j) => (
                <li key={j} className="flex gap-3 text-sm leading-relaxed">
                  <span aria-hidden className="select-none">{item.icon}</span>
                  <span className="opacity-85">
                    {item.text}
                    {item.count && (
                      <span className="ml-1.5 whitespace-nowrap rounded bg-korange px-1.5 py-0.5 text-[11px] font-bold text-[#1A1410]">
                        {SUFFIX[item.count](COUNTS[item.count])}
                      </span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ol>
    </main>
  );
}
