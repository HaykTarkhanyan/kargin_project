import { Bot, InlineKeyboard, InlineQueryResultBuilder } from "grammy";
import type { Sketch } from "../../web/lib/types";
import { byId, randomSketch } from "./data";
import {
  cardKeyboard, cardText, decodeState, feedbackPrompt, inlineDescription, isFeedbackPrompt,
  newState, type Panel, queryFromPrompt, resultsMessage, runSearch, searchTop, siteUrl,
  startKeyboard, startText, type ViewState,
} from "./cards";
import { logEvent } from "./log";
import { sendFeedback } from "./feedback";

const HTML = { parse_mode: "HTML" as const };

export function createBot(token: string): Bot {
  const bot = new Bot(token);

  const sendCard = (ctx: { reply: (t: string, o?: object) => Promise<unknown> }, s: Sketch) =>
    ctx.reply(cardText(s), { ...HTML, reply_markup: cardKeyboard(s) });

  const replySearch = async (
    ctx: { reply: (t: string, o?: object) => Promise<unknown>; from?: { id: number } },
    q: string, mode: "bot" | "bot-browse" = "bot",
  ) => {
    const state = newState(q);
    const results = runSearch(state);
    logEvent(ctx.from?.id, "search", { query: q, mode, resultCount: results.length });
    const { text, keyboard } = resultsMessage(state, results);
    await ctx.reply(text, { ...HTML, reply_markup: keyboard });
  };

  const editResults = async (
    ctx: { editMessageText: (t: string, o?: object) => Promise<unknown> },
    state: ViewState, panel: Panel = null,
  ) => {
    const { text, keyboard } = resultsMessage(state, runSearch(state), panel);
    await ctx.editMessageText(text, { ...HTML, reply_markup: keyboard });
  };

  bot.command(["start", "help"], (ctx) =>
    ctx.reply(startText(ctx.me.username), { ...HTML, reply_markup: startKeyboard() }),
  );

  // Browse mode: the whole archive, filter down without typing anything.
  bot.command("browse", (ctx) => replySearch(ctx, "", "bot-browse"));
  bot.callbackQuery("b", async (ctx) => {
    await ctx.answerCallbackQuery();
    await replySearch(ctx, "", "bot-browse");
  });

  bot.command("random", async (ctx) => {
    const s = randomSketch();
    logEvent(ctx.from?.id, "open", { sketchId: s.id, query: "random" });
    await sendCard(ctx, s);
  });

  // Any plain text = a search — PRIVATE chats only. In groups Telegram delivers
  // every /command to every bot (even ones aimed at other bots), and answering
  // those would be noise; there, the bot reacts only to its own commands and
  // inline queries. Slash-prefixed text here is an unknown command — nudge.
  // Ask for a report. Sent with force_reply so the reply carries this prompt
  // back to us — the bot scales to zero and cannot remember who is mid-report.
  const askForReport = (
    ctx: { reply: (t: string, o?: object) => Promise<unknown> }, query: string,
  ) => ctx.reply(feedbackPrompt(query), {
    ...HTML,
    reply_markup: { force_reply: true, input_field_placeholder: "Նկարագրիր սքեթչը…" },
  });

  bot.command("feedback", (ctx) => askForReport(ctx, ""));
  bot.callbackQuery(/^fb(?::([\s\S]*))?$/, async (ctx) => {
    await ctx.answerCallbackQuery();
    await askForReport(ctx, ctx.match[1] ?? "");
  });

  bot.on("message:text", async (ctx) => {
    if (ctx.chat.type !== "private") return;
    const q = ctx.message.text.trim();

    // A reply to our own prompt is a report, not a search.
    const answering = ctx.message.reply_to_message;
    if (answering && "text" in answering && isFeedbackPrompt(answering.text)) {
      try {
        await sendFeedback(ctx.from?.id, q, queryFromPrompt(answering.text ?? ""));
        await ctx.reply("✓ Ստացանք, շնորհակալությո՛ւն։ Կնայենք։");
      } catch (e) {
        // Never claim a report landed when it did not — they would not send it twice.
        console.warn("bot feedback failed", e);
        await ctx.reply("Չստացվեց ուղարկել 😕 Փորձի՛ր մի փոքր ուշ։");
      }
      return;
    }

    if (q.startsWith("/")) {
      await ctx.reply("Այդպիսի հրաման չկա 🤷 Պարզապես գրիր՝ ինչ ես փնտրում, կամ /random");
      return;
    }
    await replySearch(ctx, q);
  });

  // One-tap example searches from the /start message.
  bot.callbackQuery(/^q:(.+)$/, async (ctx) => {
    await ctx.answerCallbackQuery();
    await replySearch(ctx, ctx.match[1]);
  });

  bot.callbackQuery("r", async (ctx) => {
    await ctx.answerCallbackQuery();
    const s = randomSketch();
    logEvent(ctx.from.id, "open", { sketchId: s.id, query: "random" });
    await sendCard(ctx, s);
  });

  bot.callbackQuery(/^s:(.+)$/, async (ctx) => {
    const s = byId(ctx.match[1]);
    if (!s) { await ctx.answerCallbackQuery({ text: "Չգտնվեց 😕" }); return; }
    await ctx.answerCallbackQuery();
    logEvent(ctx.from.id, "open", { sketchId: s.id });
    await sendCard(ctx, s);
  });

  // v: re-render with the encoded state (paging, closing a panel, clearing all).
  bot.callbackQuery(/^v:([\s\S]+)$/, async (ctx) => {
    await ctx.answerCallbackQuery();
    const state = decodeState(ctx.match[1]);
    if (state) await editResults(ctx, state);
  });

  // V: a filter value was applied or cleared — same render, but logged.
  bot.callbackQuery(/^V:([\s\S]+)$/, async (ctx) => {
    await ctx.answerCallbackQuery();
    const state = decodeState(ctx.match[1]);
    if (!state) return;
    const results = runSearch(state);
    logEvent(ctx.from.id, "search", { query: state.q, mode: "bot-filter", resultCount: results.length });
    const { text, keyboard } = resultsMessage(state, results);
    await ctx.editMessageText(text, { ...HTML, reply_markup: keyboard });
  });

  // p:<panel>: unfold a filter panel (location / actor / duration) in place.
  bot.callbackQuery(/^p:(l|a|d):([\s\S]+)$/, async (ctx) => {
    await ctx.answerCallbackQuery();
    const state = decodeState(ctx.match[2]);
    if (state) await editResults(ctx, state, ctx.match[1] as Panel);
  });

  // Inline mode: @bot <query> in any chat. Empty query = most-viewed sketches.
  bot.on("inline_query", async (ctx) => {
    const q = ctx.inlineQuery.query.trim();
    const results = searchTop(q).slice(0, 10).map((s) =>
      InlineQueryResultBuilder.article(s.id, s.title, {
        description: inlineDescription(s),
        thumbnail_url: s.thumbnail || undefined,
        reply_markup: new InlineKeyboard().url("🌐 Բացել կայքում", siteUrl(s)),
      }).text(cardText(s), HTML),
    );
    await ctx.answerInlineQuery(results, { cache_time: 300 });
  });

  // Fires when someone actually sends an inline result into a chat (requires
  // /setinlinefeedback in BotFather; without it this just never triggers).
  bot.on("chosen_inline_result", (ctx) => {
    logEvent(ctx.from.id, "open", { sketchId: ctx.chosenInlineResult.result_id, mode: "inline" });
  });

  // Buttons from messages older than the current callback grammar land here.
  bot.on("callback_query:data", (ctx) =>
    ctx.answerCallbackQuery({ text: "Հին կոճակ է 🤷 Գրիր նոր որոնում կամ /browse" }),
  );

  // A handler error must never take the bot down.
  bot.catch((err) => console.error("bot handler error:", err.error));

  return bot;
}

export const COMMANDS = [
  { command: "browse", description: "Զննել արխիվը զտիչներով 🗂" },
  { command: "random", description: "Պատահական սքեթչ 🎲" },
  { command: "feedback", description: "Ասա՝ ինչ սքեթչ չգտար ✍️" },
  { command: "help", description: "Ինչպես փնտրել" },
];
