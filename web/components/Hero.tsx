import { formatViews } from "@/lib/format";

export default function Hero({ total, withDialogue, totalViews, totalHours, onSearch, query }:
  { total: number; withDialogue: number; totalViews: number; totalHours: number; onSearch: (q: string) => void; query: string }) {
  return (
    <section className="border-b-2 border-ink px-8 py-14">
      <h1 className="font-display text-6xl leading-none" style={{ maxWidth: "18ch" }}>
        Գտի՛ր <span className="text-kred">ցանկացած</span> պահը
      </h1>
      <p className="mt-4 max-w-[58ch] text-base opacity-70">
        {total} սքեթչ՝ տող առ տող։ Որոնիր երկխոսությունը, անցիր ուղիղ YouTube-ի այդ վայրկյանին։
      </p>
      <div className="mt-7 flex max-w-[720px] k-border k-shadow rounded-lg bg-white">
        <span className="flex items-center pl-5 pr-1 text-xl font-bold text-kred">⌕</span>
        <input value={query} onChange={(e) => onSearch(e.target.value)} autoFocus
          placeholder="որոնիր երկխոսություն, դերասան, վայր…"
          className="flex-1 bg-transparent px-2 py-4 text-[17px] outline-none" />
      </div>
      <div className="mt-5 flex gap-10">
        <Stat n={String(total)} l="սքեթչ" c="text-kred" />
        <Stat n={`${totalHours}ժ`} l="արխիվ" c="text-kblue" />
        <Stat n={formatViews(totalViews)} l="դիտում" c="text-korange" />
      </div>
      <p className="mt-3 text-xs text-muted">{withDialogue} սքեթչ ունի համադրված տեքստ</p>
    </section>
  );
}
function Stat({ n, l, c }: { n: string; l: string; c: string }) {
  return <div><div className={`font-display text-3xl ${c}`}>{n}</div><div className="mt-1 text-[10px] font-bold uppercase tracking-widest text-muted">{l}</div></div>;
}
