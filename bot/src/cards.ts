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
import { ALL, LOCATIONS } from "./data";

export const PAGE = 6;

/** locIdx indexes LOCATIONS; null = no filter. Same Filters the website uses. */
export function searchTop(query: string, locIdx: number | null = null): Sketch[] {
  const loc = locIdx !== null ? LOCATIONS[locIdx] : undefined;
  return searchSketches(query, ALL, loc ? { location: [loc] } : {}, "views");
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
  // switchInline opens Telegram's chat picker and pre-fills "@bot <title>" —
  // the exact title ranks the sketch first (title weight 4), so the tapped
  // sketch is what lands in the chosen chat.
  return new InlineKeyboard()
    .url("🌐 Կայքում", siteUrl(s))
    .switchInline("📤 Կիսվել", s.title)
    .row()
    .text("🎲 Էլի մեկը", "r");
}

/** Telegram caps callback_data at 64 BYTES (Armenian chars are 2 each). */
export function safeCallback(data: string): string | null {
  return Buffer.byteLength(data, "utf8") <= 64 ? data : null;
}

/** Paging: `m:` unfiltered, `M:<locIdx>:` filtered. */
export function moreCallback(query: string, offset: number, locIdx: number | null = null): string | null {
  return safeCallback(locIdx === null ? `m:${offset}:${query}` : `M:${locIdx}:${offset}:${query}`);
}

function clip(v: string, max: number): string {
  return v.length > max ? `${v.slice(0, max - 1)}…` : v;
}

/** One list entry: title line + a hook line (famous line, else actors) + numbers. */
function resultEntry(n: number, s: Sketch): string {
  const hook = s.textCommon ? `★ «${escapeHtml(clip(s.textCommon, 60))}»` : `👥 ${escapeHtml(s.actors.join(", ") || "—")}`;
  return [
    `<b>${n}.</b> ${escapeHtml(clip(s.title, 70))}`,
    `${hook} · ⏱ ${formatDuration(s.durationSec)} · 👁 ${formatViews(s.viewCount)}`,
  ].join("\n");
}

/**
 * The search reply: a rich descriptive list in the message body (buttons can't
 * hold images or second lines) + compact number buttons. The 🖼 button flips
 * the same query into inline mode — the only Telegram surface with real
 * per-result thumbnails. A third row exposes the location filter: closed it
 * reads «📍 Ըստ վայրի» (or the active «📍 Տուն ✕» chip); `picker: true`
 * renders the location choices instead.
 */
export function resultsMessage(
  query: string, results: Sketch[], offset: number,
  locIdx: number | null = null, picker = false,
): { text: string; keyboard: InlineKeyboard } {
  const locLabel = locIdx !== null ? LOCATIONS[locIdx] : null;
  const header = locLabel
    ? `🔍 «${escapeHtml(query)}» · 📍 ${escapeHtml(locLabel)} — ${results.length} արդյունք`
    : `🔍 «${escapeHtml(query)}» — ${results.length} արդյունք`;

  if (results.length === 0) {
    const text = locLabel
      ? `${header}\n\nԱյդ վայրում ոչինչ չգտնվեց 😕 Հանիր զտիչը կամ ընտրիր այլ վայր։`
      : [
          `Ոչինչ չգտնվեց «${escapeHtml(query)}» հարցումով 😕`,
          "",
          "Փորձիր՝",
          "• 💬 ռեպլիկա՝ «տոռմուզ», լատինատառ «tormuz» կամ ռուսատառ «тормуз»",
          "• 👤 դերասան՝ «Հայկո»",
          "• 📍 վայր՝ «Հիվանդանոց», «Խանութ»",
          "• 🎬 տեսարան՝ «հարսանիք», «կով»",
        ].join("\n");
    const kb = new InlineKeyboard();
    if (locLabel) {
      const clear = safeCallback(`l:-:${query}`);
      if (clear) kb.text("✕ Հանել զտիչը", clear).row();
    }
    kb.text("🎲 Պատահական", "r");
    return { text, keyboard: kb };
  }

  const page = results.slice(offset, offset + PAGE);
  const text = [header, "", ...page.map((s, i) => resultEntry(offset + i + 1, s))].join("\n\n");

  const kb = new InlineKeyboard();
  for (const [i, s] of page.entries()) kb.text(String(offset + i + 1), `s:${s.id}`);
  kb.row().switchInlineCurrent("🖼 Նկարներով", query);
  if (results.length > offset + PAGE) {
    const cb = moreCallback(query, offset + PAGE, locIdx);
    if (cb) kb.text(`➕ Ավելին (${results.length - offset - PAGE})`, cb);
  }

  if (picker) {
    // Location choices, three per row; the active one is checked and clears.
    for (const [i, loc] of LOCATIONS.entries()) {
      if (i % 3 === 0) kb.row();
      const active = i === locIdx;
      const cb = safeCallback(active ? `l:-:${query}` : `l:${i}:${query}`);
      if (cb) kb.text(`${active ? "✓ " : ""}${loc}`, cb);
    }
  } else {
    // The chip reopens the picker (switch or clear there); closed state opens it too.
    const toggle = safeCallback(`f:${locIdx ?? "-"}:${query}`);
    if (toggle) kb.row().text(locLabel ? `📍 ${locLabel} ✕` : "📍 Ըստ վայրի", toggle);
  }
  return { text, keyboard: kb };
}

/** Canned searches offered as one-tap buttons under /start — one per search TYPE. */
export const EXAMPLES = [
  { emoji: "💬", q: "տոռմուզ" },     // catchphrase / dialogue
  { emoji: "👤", q: "Հայկո" },       // actor
  { emoji: "📍", q: "Հիվանդանոց" },  // location facet
  { emoji: "🎵", q: "Челентано" },   // recognized song
  { emoji: "🎬", q: "կով" },         // visual scene annotation
] as const;

export function startText(username: string): string {
  return [
    "Բարև՛ 👋 Ես գտնում եմ Կարգին Հաղորդման սքեթչերը՝ գրիր որևէ բան, ես կփնտրեմ ամեն տեղ.",
    "",
    "• 💬 ռեպլիկա — «տոռմուզ», լատինատառ «tormuz», ռուսատառ «тормуз»",
    "• 👤 դերասան — «Հայկո», «Մկո»",
    "• 📍 վայր — «Հիվանդանոց», «Խանութ», «Գրասենյակ»",
    "• 🎵 երգ — «Челентано», «Thriller»",
    "• 🎬 տեսարան — «հարսանիք», «կով», «казино»",
    "",
    `💡 Ցանկացած չաթում գրիր <code>@${username} հարցում</code>, ընտրիր սքեթչը — ու այն կհայտնվի հենց այդ չաթում՝ նկարներով ցուցակից։ Խմբերում փնտրելու միակ ձևը սա է։`,
    "",
    "Կամ սկսիր հենց հիմա 👇",
  ].join("\n");
}

export function startKeyboard(): InlineKeyboard {
  const kb = new InlineKeyboard();
  for (const [i, e] of EXAMPLES.entries()) {
    if (i === 3) kb.row(); // 3 + 2 layout
    kb.text(`${e.emoji} ${e.q}`, `q:${e.q}`);
  }
  return kb.row().text("🎲 Պատահական", "r").url("🌐 Կայքը", SITE_ORIGIN);
}

/** Inline-result subtitle: the famous line sells the sketch better than numbers. */
export function inlineDescription(s: Sketch): string {
  const hook = s.textCommon ? `«${s.textCommon}»` : s.actors.join(", ");
  return `${hook}\n⏱ ${formatDuration(s.durationSec)} · 👁 ${formatViews(s.viewCount)} · ${s.location}`;
}
