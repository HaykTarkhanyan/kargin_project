"use client";
import { useEffect, useRef } from "react";
import { formatViews } from "@/lib/format";
import { BOT_URL, BOT_USERNAME } from "@/lib/site";

export default function Hero({ total, withDialogue, totalViews, totalHours, onSearch, query }:
  { total: number; withDialogue: number; totalViews: number; totalHours: number; onSearch: (q: string) => void; query: string }) {
  const input = useRef<HTMLInputElement>(null);
  // Focus on desktop only. Plain autoFocus opens the on-screen keyboard the
  // moment a phone loads the page, hiding the results underneath it and
  // scrolling the visitor somewhere they did not ask to go.
  useEffect(() => {
    if (window.matchMedia("(min-width: 1024px) and (pointer: fine)").matches) input.current?.focus();
  }, []);
  return (
    // No padding of its own: the parent section in SearchExperience already
    // insets this column, and doubling it cost 32px a side on a 390px screen.
    <section className="border-b-2 border-ink pb-7 sm:pb-10">
      <h1 className="font-display text-4xl leading-none sm:text-6xl" style={{ maxWidth: "18ch" }}>
        Գտի՛ր <span className="text-kred">ցանկացած</span> պահը
      </h1>
      <p className="mt-3 max-w-[58ch] text-sm opacity-70 sm:mt-4 sm:text-base">
        {total} սքեթչ՝ տող առ տող։ Որոնիր երկխոսությունը, անցիր ուղիղ YouTube-ի այդ վայրկյանին։
      </p>
      <div className="mt-5 flex max-w-[720px] k-border k-shadow rounded-lg bg-surface sm:mt-7">
        <span className="flex items-center pl-5 pr-1 text-xl font-bold text-kred">⌕</span>
        {/* text-[17px]: anything under 16px makes iOS Safari zoom the page on focus. */}
        <input ref={input} value={query} onChange={(e) => onSearch(e.target.value)}
          type="search" enterKeyHint="search" autoComplete="off" autoCorrect="off" autoCapitalize="none"
          placeholder="որոնիր երկխոսություն, դերասան, վայր…"
          className="flex-1 bg-transparent px-2 py-4 text-[17px] outline-none [&::-webkit-search-cancel-button]:appearance-none" />
      </div>
      <div className="mt-4 flex gap-6 sm:mt-5 sm:gap-10">
        <Stat n={String(total)} l="սքեթչ" c="text-kred" />
        <Stat n={`${totalHours}ժ`} l="արխիվ" c="text-kblue" />
        <Stat n={formatViews(totalViews)} l="դիտում" c="text-korange" />
      </div>
      <p className="mt-3 text-xs text-muted">{withDialogue} սքեթչ ունի համադրված տեքստ</p>
      <a href={BOT_URL} target="_blank" rel="noreferrer"
        className="mt-3 inline-flex min-h-11 items-center gap-2 rounded-full border-2 border-ink bg-surface px-4 py-2 text-xs font-bold hover:bg-ink hover:text-paper sm:mt-4">
        <span className="text-kblue">✈</span> Նույն որոնումը Telegram-ում՝ @{BOT_USERNAME}
      </a>
    </section>
  );
}
function Stat({ n, l, c }: { n: string; l: string; c: string }) {
  return <div><div className={`font-display text-3xl ${c}`}>{n}</div><div className="mt-1 text-[10px] font-bold uppercase tracking-widest text-muted">{l}</div></div>;
}
