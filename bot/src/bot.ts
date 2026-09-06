import { Bot, InlineKeyboard, InlineQueryResultBuilder } from "grammy";
import type { Sketch } from "../../web/lib/types";
import { byId, randomSketch } from "./data";
import {
  cardKeyboard, cardText, inlineDescription, resultsMessage,
  searchTop, siteUrl, startKeyboard, startText,
} from "./cards";
import { logEvent } from "./log";

const HTML = { parse_mode: "HTML" as const };

export function createBot(token: string): Bot {
  const bot = new Bot(token);

  const sendCard = (ctx: { reply: (t: string, o?: object) => Promise<unknown> }, s: Sketch) =>
    ctx.reply(cardText(s), { ...HTML, reply_markup: cardKeyboard(s) });

  const replySearch = async (
    ctx: { reply: (t: string, o?: object) => Promise<unknown>; from?: { id: number } },
    q: string,
  ) => {
    const results = searchTop(q);
    logEvent(ctx.from?.id, "search", { query: q, mode: "bot", resultCount: results.length });
    const { text, keyboard } = resultsMessage(q, results, 0);
    await ctx.reply(text, { ...HTML, reply_markup: keyboard });
  };

  bot.command(["start", "help"], (ctx) =>
    ctx.reply(startText(ctx.me.username), { ...HTML, reply_markup: startKeyboard() }),
  );

  bot.command("random", async (ctx) => {
    const s = randomSketch();
    logEvent(ctx.from?.id, "open", { sketchId: s.id, query: "random" });
    await sendCard(ctx, s);
  });

  // Any plain text = a search. Slash-prefixed text that reached here is an
  // unknown command — nudge instead of searching for "/whatever".
  bot.on("message:text", async (ctx) => {
    const q = ctx.message.text.trim();
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

  // Re-render the results message in place (paging, filter picker, filter apply).
  const editResults = async (
    ctx: { editMessageText: (t: string, o?: object) => Promise<unknown> },
    q: string, offset: number, locIdx: number | null, picker = false,
  ) => {
    const { text, keyboard } = resultsMessage(q, searchTop(q, locIdx), offset, locIdx, picker);
    await ctx.editMessageText(text, { ...HTML, reply_markup: keyboard });
  };

  // "More results": next page, unfiltered (m:) or location-filtered (M:).
  bot.callbackQuery(/^m:(\d+):([\s\S]+)$/, async (ctx) => {
    await ctx.answerCallbackQuery();
    await editResults(ctx, ctx.match[2], Number(ctx.match[1]), null);
  });
  bot.callbackQuery(/^M:(\d+):(\d+):([\s\S]+)$/, async (ctx) => {
    await ctx.answerCallbackQuery();
    await editResults(ctx, ctx.match[3], Number(ctx.match[2]), Number(ctx.match[1]));
  });

  // «📍» button: unfold the location choices under the current results.
  bot.callbackQuery(/^f:(-|\d+):([\s\S]+)$/, async (ctx) => {
    await ctx.answerCallbackQuery();
    const locIdx = ctx.match[1] === "-" ? null : Number(ctx.match[1]);
    await editResults(ctx, ctx.match[2], 0, locIdx, true);
  });

  // Location picked (l:<i>) or cleared (l:-): re-render filtered from page one.
  bot.callbackQuery(/^l:(-|\d+):([\s\S]+)$/, async (ctx) => {
    await ctx.answerCallbackQuery();
    const locIdx = ctx.match[1] === "-" ? null : Number(ctx.match[1]);
    const q = ctx.match[2];
    const results = searchTop(q, locIdx);
    logEvent(ctx.from.id, "search", { query: q, mode: "bot-filter", resultCount: results.length });
    const { text, keyboard } = resultsMessage(q, results, 0, locIdx);
    await ctx.editMessageText(text, { ...HTML, reply_markup: keyboard });
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

  // A handler error must never take the bot down.
  bot.catch((err) => console.error("bot handler error:", err.error));

  return bot;
}

export const COMMANDS = [
  { command: "random", description: "Պատահական սքեթչ 🎲" },
  { command: "help", description: "Ինչպես փնտրել" },
];
