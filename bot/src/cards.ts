/**
 * Pure message/keyboard builders — everything here is unit-testable without
 * the Telegram API. Search itself is the website's implementation
 * (web/lib/search.ts): same transliteration, same fuzzy, no drift.
 */
import { InlineKeyboard } from "grammy";
import { searchSketches } from "../../web/lib/search";
import { formatDuration, formatViews } from "../../web/lib/format";
import { SITE_ORIGIN } from "../../web/lib/site";
import type { Sketch } from "../../web/lib/types";
import { ALL } from "./data";

export const PAGE = 6;

export function searchTop(query: string): Sketch[] {
  return searchSketches(query, ALL, {}, "views");
}

export function escapeHtml(s: string): string {
  return s.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

/** The sketch card (HTML parse mode). The bare youtu.be URL makes Telegram
 *  render its in-chat video player, so the sketch plays without leaving the app. */
export function cardText(s: Sketch): string {
  const lines = [`🎬 <b>${escapeHtml(s.title)}</b>`];
  if (s.textCommon) lines.push("", `★ «${escapeHtml(s.textCommon)}»`);
  lines.push(
    "",
    `👥 ${escapeHtml(s.actors.join(", ") || "—")} · 📍 ${escapeHtml(s.location)}`,
    `⏱ ${formatDuration(s.durationSec)} · 👁 ${formatViews(s.viewCount)}`,
    "",
    `▶️ https://youtu.be/${s.videoId}`,
  );
  return lines.join("\n");
}

export function siteUrl(s: Sketch): string {
  return `${SITE_ORIGIN}/sketch/${s.id}/`;
}

export function cardKeyboard(s: Sketch): InlineKeyboard {
  return new InlineKeyboard().url("🌐 Բացել կայքում", siteUrl(s)).text("🎲 Պատահական", "r");
}

function buttonLabel(i: number, s: Sketch): string {
  const title = s.title.length > 42 ? `${s.title.slice(0, 41)}…` : s.title;
  return `${i + 1}. ${title} · ${formatDuration(s.durationSec)}`;
}

/** Telegram caps callback_data at 64 BYTES (Armenian chars are 2 each). */
export function moreCallback(query: string, offset: number): string | null {
  const data = `m:${offset}:${query}`;
  return Buffer.byteLength(data, "utf8") <= 64 ? data : null;
}

export function resultsKeyboard(results: Sketch[], query: string, offset: number): InlineKeyboard {
  // .row() only BETWEEN buttons — a trailing .row() leaves an empty row in the markup.
  const kb = new InlineKeyboard();
  for (const [i, s] of results.slice(offset, offset + PAGE).entries()) {
    if (i > 0) kb.row();
    kb.text(buttonLabel(offset + i, s), `s:${s.id}`);
  }
  if (results.length > offset + PAGE) {
    const cb = moreCallback(query, offset + PAGE);
    if (cb) kb.row().text(`➕ Ավելին (${results.length - offset - PAGE})`, cb);
  }
  return kb;
}

export function resultsText(query: string, count: number): string {
  if (count === 0) {
    return [
      `Ոչինչ չգտնվեց «${escapeHtml(query)}» հարցումով 😕`,
      "",
      "Փորձիր՝",
      "• կարճ բառ կամ արտահայտություն («տոռմուզ», «մետաղալոմ»)",
      "• լատինատառ կամ ռուսատառ («tormuz», «тормуз»)",
      "• դերասանի անուն («Հայկո»)",
    ].join("\n");
  }
  return `🔍 «${escapeHtml(query)}» — ${count} արդյունք`;
}

export const START_TEXT = [
  "Բարև՛ 👋 Ես գտնում եմ Կարգին Հաղորդման սքեթչերը՝ ռեպլիկայով, դերասանով, երգով կամ տեսարանով։",
  "",
  "Պարզապես գրիր՝ ինչ ես փնտրում.",
  "• «տոռմուզ» կամ լատինատառ «tormuz»",
  "• «Հայկո» — դերասանի բոլոր սքեթչերը",
  "• «казино», «հարսանիք», «կով» — տեսարանով",
  "",
  "💡 Ցանկացած չաթում գրիր <code>@բոտի_անունը հարցում</code> — սքեթչը կկիսվես առանց չաթից դուրս գալու։",
  "",
  "🎲 /random — պատահական սքեթչ",
].join("\n");
