import { Bot, InlineKeyboard, InlineQueryResultBuilder } from "grammy";
import { SITE_ORIGIN } from "../../web/lib/site";
import { formatDuration, formatViews } from "../../web/lib/format";
import type { Sketch } from "../../web/lib/types";
import { byId, randomSketch } from "./data";
import {
  cardKeyboard, cardText, PAGE, resultsKeyboard, resultsText, searchTop, siteUrl, START_TEXT,
} from "./cards";
import { logEvent } from "./log";

const HTML = { parse_mode: "HTML" as const };

export function createBot(token: string): Bot {
  const bot = new Bot(token);

  const sendCard = (ctx: { reply: (t: string, o?: object) => Promise<unknown> }, s: Sketch) =>
    ctx.reply(cardText(s), { ...HTML, reply_markup: cardKeyboard(s) });

  bot.command(["start", "help"], (ctx) =>
    ctx.reply(START_TEXT, {
      ...HTML,
      reply_markup: new InlineKeyboard().text("🎲 Պատահական", "r").url("🌐 Կայքը", SITE_ORIGIN),
    }),
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
    const results = searchTop(q);
    logEvent(ctx.from?.id, "search", { query: q, mode: "bot", resultCount: results.length });
    await ctx.reply(resultsText(q, results.length), {
      ...HTML,
      reply_markup: results.length
        ? resultsKeyboard(results, q, 0)
        : new InlineKeyboard().text("🎲 Պատահական", "r"),
    });
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

  // "More results": swap the keyboard in place for the next page.
  bot.callbackQuery(/^m:(\d+):([\s\S]+)$/, async (ctx) => {
    await ctx.answerCallbackQuery();
    const offset = Number(ctx.match[1]);
    const q = ctx.match[2];
    const results = searchTop(q);
    await ctx.editMessageReplyMarkup({ reply_markup: resultsKeyboard(results, q, offset) });
  });

  // Inline mode: @bot <query> in any chat. Empty query = most-viewed sketches.
  bot.on("inline_query", async (ctx) => {
    const q = ctx.inlineQuery.query.trim();
    const results = searchTop(q).slice(0, 10).map((s) =>
      InlineQueryResultBuilder.article(s.id, s.title, {
        description: `⏱ ${formatDuration(s.durationSec)} · 👁 ${formatViews(s.viewCount)} · ${s.location}`,
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

// Referenced by tests to assert paging math stays in sync with the keyboard.
export { PAGE };
