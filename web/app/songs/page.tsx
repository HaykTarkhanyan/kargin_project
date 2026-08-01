import Link from "next/link";
import { ALL } from "@/lib/data";
import { Card, BarList } from "@/components/stats/Charts";

// Server component: everything below is computed once at build time from the
// real payload, so no dataset and no aggregation reaches the client.

const withSongs = ALL.filter((s) => s.songs?.length);
const pairs = withSongs.flatMap((s) => s.songs!.map((song) => ({ s, song })));

function tally(items: string[]): { label: string; value: number }[] {
  const m = new Map<string, number>();
  for (const x of items) if (x) m.set(x, (m.get(x) ?? 0) + 1);
  return [...m].map(([label, value]) => ({ label, value })).sort((a, b) => b.value - a.value);
}

const topArtists = tally(pairs.map((p) => p.song.artist)).slice(0, 12);
const topTracks = tally(pairs.map((p) => `${p.song.artist} — ${p.song.title}`)).slice(0, 12);
const topLabels = tally(pairs.map((p) => p.song.label)).slice(0, 10);

// Release decade. `released` is the date of the RELEASE Shazam matched, which
// can be a later compilation of an older recording — so this is "when the
// matched release came out", not strictly when the music was made.
const decades = tally(
  pairs
    .map((p) => parseInt(p.song.released, 10))
    .filter((y) => y >= 1900 && y <= 2030)
    .map((y) => `${Math.floor(y / 10) * 10}s`),
).sort((a, b) => a.label.localeCompare(b.label));

// How many distinct tracks per sketch.
const perSketch = tally(
  withSongs.map((s) => {
    const n = s.songs!.length;
    return n >= 5 ? "5+" : String(n);
  }),
).sort((a, b) => a.label.localeCompare(b.label));

// Where in the sketch the music sits, as a fraction of its duration. Answers
// whether music is an intro sting or runs throughout.
const positions = tally(
  pairs.flatMap(({ s, song }) =>
    s.durationSec
      ? song.at.map((sec) => {
          const fifth = Math.min(4, Math.floor((sec / s.durationSec!) * 5));
          return ["0–20%", "20–40%", "40–60%", "60–80%", "80–100%"][fifth];
        })
      : [],
  ),
).sort((a, b) => a.label.localeCompare(b.label));

const distinctTracks = new Set(pairs.map((p) => `${p.song.artist}|${p.song.title}`)).size;
const distinctArtists = new Set(pairs.map((p) => p.song.artist)).size;
const totalMoments = pairs.reduce((n, p) => n + p.song.at.length, 0);

export default function SongsPage() {
  const stat: [string, string, string][] = [
    [String(withSongs.length), "սքեթչ երաժշտությամբ", "#D90012"],
    [String(distinctTracks), "տարբեր երգ", "#0033A0"],
    [String(distinctArtists), "կատարող", "#F2A800"],
    [String(totalMoments), "հնչման պահ", "#D90012"],
  ];

  return (
    <main className="mx-auto max-w-5xl px-4 py-8 sm:px-7">
      <h1 className="mb-3 font-display text-4xl">Երաժշտություն</h1>
      <p className="mb-5 max-w-[70ch] text-sm leading-relaxed text-muted">
        Սքեթչներում հնչող երգերը ճանաչվել են բուն ձայնից։ Ցույց են տրված միայն այն համընկնումները,
        որոնք հաստատվել են կրկնակի ստուգմամբ։ Աշխատանքը դեռ ընթացքի մեջ է, ուստի ցուցակը կլրացվի։
      </p>

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {stat.map(([n, l, c]) => (
          <div key={l} className="k-border k-shadow rounded-lg bg-card p-3">
            <div className="font-display text-2xl" style={{ color: c }}>{n}</div>
            <div className="text-[10px] font-bold uppercase tracking-widest text-muted">{l}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        <Card title="Ամենահաճախ հնչող կատարողները" note="քանի սքեթչում է հանդիպում">
          <BarList rows={topArtists} color="#D90012" />
        </Card>
        <Card title="Ամենահաճախ հնչող երգերը" note="քանի սքեթչում է հանդիպում">
          <BarList rows={topTracks} color="#0033A0" />
        </Card>
        <Card title="Ձայնագրության տասնամյակը" note="ըստ ճանաչված թողարկման տարեթվի">
          <BarList rows={decades} color="#F2A800" />
        </Card>
        <Card title="Քանի՞ երգ մեկ սքեթչում">
          <BarList rows={perSketch} color="#0033A0" />
        </Card>
        <Card title="Որտե՞ղ է հնչում երաժշտությունը" note="սքեթչի տևողության որ հատվածում" full>
          <BarList rows={positions} color="#D90012" />
        </Card>
        <Card title="Ձայնագրող ընկերությունները" note="ըստ ճանաչված թողարկման" full>
          <BarList rows={topLabels} color="#0033A0" />
        </Card>
      </div>

      <h2 className="mt-10 mb-3 font-display text-2xl">Բոլոր սքեթչները երաժշտությամբ</h2>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {withSongs
          .slice()
          .sort((a, b) => (b.songs?.length ?? 0) - (a.songs?.length ?? 0) || (b.viewCount ?? 0) - (a.viewCount ?? 0))
          .map((s) => (
            <Link key={s.id} href={`/sketch/${s.id}`} className="k-border rounded-lg bg-card px-3 py-2 text-sm hover:bg-paper2">
              <div className="flex items-baseline justify-between gap-2">
                <span className="truncate font-bold">{s.title}</span>
                <span className="shrink-0 rounded bg-korange px-1.5 py-0.5 text-[11px] font-bold text-[#1A1410]">🎵 {s.songs!.length}</span>
              </div>
              <div className="truncate text-xs text-muted">{s.songs!.map((x) => x.artist).join(" · ")}</div>
            </Link>
          ))}
      </div>
    </main>
  );
}
