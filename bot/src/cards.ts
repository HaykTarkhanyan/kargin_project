/**
 * Pure message/keyboard builders — everything here is unit-testable without
 * the Telegram API. Search itself is the website's implementation
 * (web/lib/search.ts): same transliteration, same fuzzy, no drift.
 */
import { InlineKeyboard } from "grammy";
import { type Filters, searchSketches } from "../../web/lib/search";
import { formatDuration, formatViews } from "../../web/lib/format";
import { SITE_ORIGIN } from "../../web/lib/site";
import type { Sketch } from "../../web/lib/types";
import { ACTORS, ALL, LOCATIONS } from "./data";

export const PAGE = 6;

export const DURATIONS = [
  { key: "<2" as const, label: "մինչև 2ր" },
  { key: "2-4" as const, label: "2–4ր" },
  { key: "4+" as const, label: "4ր+" },
];

/** Plain unfiltered search — inline mode and the /start examples. */
export function searchTop(query: string): Sketch[] {
  return searchSketches(query, ALL, {}, "views");
}

// ---------------------------------------------------------------------------
// View state — everything a results message needs to re-render itself, packed
// into each button's callback_data as `<loc>:<actor>:<dur>:<offset>:<query>`
// (indexes into the facet lists; query last so it may contain ":").
// An EMPTY query is valid: that's browse mode ("filter down without text").
// ---------------------------------------------------------------------------
export interface ViewState {
  q: string;
  loc: number | null;
  actor: number | null;
  dur: number | null;
  offset: number;
}

export const newState = (q: string): ViewState =>
  ({ q, loc: null, actor: null, dur: null, offset: 0 });

export function encodeState(s: ViewState): string {
  return `${s.loc ?? "-"}:${s.actor ?? "-"}:${s.dur ?? "-"}:${s.offset}:${s.q}`;
}

export function decodeState(data: string): ViewState | null {
  const m = /^(-|\d+):(-|\d+):(-|\d+):(\d+):([\s\S]*)$/.exec(data);
  if (!m) return null;
  const idx = (v: string) => (v === "-" ? null : Number(v));
  return { loc: idx(m[1]), actor: idx(m[2]), dur: idx(m[3]), offset: Number(m[4]), q: m[5] };
}

export function toFilters(s: ViewState): Filters {
  const f: Filters = {};
  if (s.loc !== null && LOCATIONS[s.loc]) f.location = [LOCATIONS[s.loc]];
  if (s.actor !== null && ACTORS[s.actor]) f.actors = [ACTORS[s.actor]];
  if (s.dur !== null && DURATIONS[s.dur]) f.duration = DURATIONS[s.dur].key;
  return f;
}

export function runSearch(state: ViewState): Sketch[] {
  return searchSketches(state.q, ALL, toFilters(state), "views");
}

export const hasFilters = (s: ViewState): boolean =>
  s.loc !== null || s.actor !== null || s.dur !== null;

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

export type Panel = "l" | "a" | "d" | null;

function headerLine(state: ViewState, count: number): string {
  const parts = [state.q ? `🔍 «${escapeHtml(state.q)}»` : "🗂 Բոլոր սքեթչերը"];
  if (state.loc !== null) parts.push(`📍 ${escapeHtml(LOCATIONS[state.loc])}`);
  if (state.actor !== null) parts.push(`👤 ${escapeHtml(ACTORS[state.actor])}`);
  if (state.dur !== null) parts.push(`⏱ ${DURATIONS[state.dur].label}`);
  return `${parts.join(" · ")} — ${count} արդյունք`;
}

/** A picker's value buttons: tap sets the filter (V: logs it), ✓ clears it. */
function panelRows(kb: InlineKeyboard, state: ViewState, panel: Exclude<Panel, null>): void {
  const values: string[] =
    panel === "l" ? LOCATIONS : panel === "a" ? ACTORS : DURATIONS.map((d) => d.label);
  const activeIdx = panel === "l" ? state.loc : panel === "a" ? state.actor : state.dur;
  const buttons: Array<{ label: string; cb: string }> = [];
  for (const [i, value] of values.entries()) {
    const next: ViewState = { ...state, offset: 0 };
    if (panel === "l") next.loc = i === activeIdx ? null : i;
    if (panel === "a") next.actor = i === activeIdx ? null : i;
    if (panel === "d") next.dur = i === activeIdx ? null : i;
    const cb = safeCallback(`V:${encodeState(next)}`);
    if (cb) buttons.push({ label: `${i === activeIdx ? "✓ " : ""}${value}`, cb });
  }
  for (const [i, b] of buttons.entries()) {
    if (i % 3 === 0) kb.row();
    kb.text(b.label, b.cb);
  }
}

/**
 * The results view: a rich descriptive list (buttons can't hold images or
 * second lines) + number buttons + a filter row (📍 վայր / 👤 դերասան /
 * ⏱ տևողություն). Tapping a toggle unfolds that panel's values; every button
 * carries the full encoded state so paging and filters compose. The 🖼 button
 * flips the query into inline mode — the only surface with real thumbnails.
 * With an empty query this doubles as the browse-everything view.
 */
export function resultsMessage(state: ViewState, results: Sketch[], panel: Panel = null):
  { text: string; keyboard: InlineKeyboard } {
  const header = headerLine(state, results.length);

  if (results.length === 0) {
    const kb = new InlineKeyboard();
    let text: string;
    if (hasFilters(state)) {
      text = `${header}\n\nԱյս զտիչներով ոչինչ չգտնվեց 😕`;
      const clear = safeCallback(`v:${encodeState({ ...newState(state.q) })}`);
      if (clear) kb.text("✕ Հանել զտիչները", clear).row();
    } else {
      text = [
        `Ոչինչ չգտնվեց «${escapeHtml(state.q)}» հարցումով 😕`,
        "",
        "Փորձիր՝",
        "• 💬 ռեպլիկա՝ «տոռմուզ», լատինատառ «tormuz» կամ ռուսատառ «тормуз»",
        "• 👤 դերասան՝ «Հայկո»",
        "• 📍 վայր՝ «Հիվանդանոց», «Խանութ»",
        // Anglophone on purpose: the scene descriptions are written in English,
        // so an Armenian word here searches the dialogue instead and the tip
        // quietly teaches the wrong thing.
        "• 🎬 տեսարան (անգլերեն)՝ «wedding», «lada», «cow»",
        "",
        "Կամ /browse — զննիր ամբողջ արխիվը զտիչներով։",
      ].join("\n");
    }
    kb.text("🎲 Պատահական", "r");
    // Nothing found is exactly when a report is worth most, so it is offered
    // here rather than buried in /help.
    const report = safeCallback(`fb:${state.q}`);
    kb.text("✍️ Ասա մեզ՝ ինչ չգտար", report ?? "fb");
    return { text, keyboard: kb };
  }

  const page = results.slice(state.offset, state.offset + PAGE);
  const text = [header, "", ...page.map((s, i) => resultEntry(state.offset + i + 1, s))].join("\n\n");

  const kb = new InlineKeyboard();
  for (const [i, s] of page.entries()) kb.text(String(state.offset + i + 1), `s:${s.id}`);
  kb.row().switchInlineCurrent("🖼 Նկարներով", state.q);
  if (results.length > state.offset + PAGE) {
    const cb = safeCallback(`v:${encodeState({ ...state, offset: state.offset + PAGE })}`);
    if (cb) kb.text(`➕ Ավելին (${results.length - state.offset - PAGE})`, cb);
  }

  // Filter toggles: label shows the active value; tapping an open panel closes it.
  const zeroOffset = encodeState({ ...state, offset: 0 });
  const toggles = ([
    ["l", state.loc !== null ? `📍 ${LOCATIONS[state.loc]}` : "📍 Վայր"],
    ["a", state.actor !== null ? `👤 ${ACTORS[state.actor]}` : "👤 Դերասան"],
    ["d", state.dur !== null ? `⏱ ${DURATIONS[state.dur].label}` : "⏱ Տևողություն"],
  ] as Array<[Exclude<Panel, null>, string]>)
    .map(([key, label]) => ({
      label: `${label}${panel === key ? " ▴" : ""}`,
      cb: safeCallback(panel === key ? `v:${zeroOffset}` : `p:${key}:${zeroOffset}`),
    }))
    .filter((t): t is { label: string; cb: string } => t.cb !== null);
  if (toggles.length) {
    kb.row();
    for (const t of toggles) kb.text(t.label, t.cb);
  }
  if (panel) panelRows(kb, state, panel);
  return { text, keyboard: kb };
}

// --- Reporting a sketch we are missing ------------------------------------
// The bot runs on Cloud Run and scales to zero, so it cannot hold "this user is
// writing a report" in memory between updates. Instead the prompt is sent with
// force_reply and identified by its own first character: a reply carries the
// prompt text back in reply_to_message, which is all the state that is needed.

/** Identifies our own prompt in a reply. Must stay the first character of it. */
export const FEEDBACK_MARK = "✍️";

export function feedbackPrompt(query: string): string {
  return [
    `${FEEDBACK_MARK} <b>Ի՞նչ չգտար</b>`,
    query ? `Որոնումդ՝ «${escapeHtml(query)}»` : "",
    "",
    "Պատասխանի՛ր այս հաղորդագրությանը և նկարագրիր սքեթչը՝ ի՞նչ են ասում, ո՞վ է խաղում, ի՞նչ է կատարվում։",
    "Եթե ուզում ես պատասխան ստանալ, գրի՛ր նաև կապի միջոցդ։",
  ].filter(Boolean).join("\n");
}

export function isFeedbackPrompt(text: string | undefined): boolean {
  return !!text && text.startsWith(FEEDBACK_MARK);
}

/**
 * The search a prompt was raised from, read back out of the prompt's own text.
 * Telegram hands back the rendered message, so this matches the displayed line
 * rather than the HTML that produced it.
 */
export function queryFromPrompt(text: string): string {
  return /Որոնումդ՝ «([\s\S]*?)»/.exec(text)?.[1] ?? "";
}

/** Canned searches offered as one-tap buttons under /start — one per search TYPE. */
export const EXAMPLES = [
  { emoji: "💬", q: "տոռմուզ" },     // catchphrase / dialogue
  { emoji: "👤", q: "Հայկո" },       // actor
  { emoji: "📍", q: "Հիվանդանոց" },  // location facet
  // Latin, not "Челентано": song credits are stored in Latin and the index only
  // transliterates Armenian, so a Cyrillic spelling of a Latin name reaches
  // nothing. It used to return sketches only because the old fuzzy pass was
  // loose enough to match unrelated Cyrillic dialogue.
  { emoji: "🎵", q: "Celentano" },   // recognized song
  // "Lada", not "կով": the scene annotations are English, so an Armenian word
  // demonstrates dialogue search all over again. Lada is in 45 sketches' visuals
  // and in no dialogue anywhere — it can only be found by what the AI saw.
  { emoji: "🎬", q: "Lada" },        // visual scene annotation
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
    "Տեքստ չե՞ս հիշում — /browse. ամբողջ արխիվը՝ վայրի, դերասանի ու տևողության զտիչներով։",
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
  return kb.row().text("🗂 Զննել բոլորը", "b").text("🎲 Պատահական", "r").url("🌐 Կայքը", SITE_ORIGIN);
}

/** Inline-result subtitle: the famous line sells the sketch better than numbers. */
export function inlineDescription(s: Sketch): string {
  const hook = s.textCommon ? `«${s.textCommon}»` : s.actors.join(", ");
  return `${hook}\n⏱ ${formatDuration(s.durationSec)} · 👁 ${formatViews(s.viewCount)} · ${s.location}`;
}
