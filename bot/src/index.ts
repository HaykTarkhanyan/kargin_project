/**
 * Entry point. Two modes:
 *   - polling (default): local dev — just `npm run dev` with BOT_TOKEN set.
 *   - webhook: set WEBHOOK_URL (the public HTTPS URL of this service) — used on
 *     Cloud Run. The server listens on PORT (Cloud Run injects it) and verifies
 *     Telegram's secret token header derived from the bot token.
 */
import { createHash } from "node:crypto";
import { createServer } from "node:http";
import { webhookCallback } from "grammy";
import { COMMANDS, createBot } from "./bot";

const token = process.env.BOT_TOKEN;
if (!token) throw new Error("BOT_TOKEN is required");

const bot = createBot(token);
await bot.api.setMyCommands(COMMANDS);

const webhookUrl = process.env.WEBHOOK_URL;
if (webhookUrl) {
  const secretToken = createHash("sha256").update(token).digest("hex").slice(0, 32);
  await bot.init();
  const handle = webhookCallback(bot, "http", { secretToken });
  const port = Number(process.env.PORT ?? 8080);
  createServer((req, res) => {
    // NOT /healthz: Google's frontend reserves z-suffixed paths on run.app
    // URLs and answers them with its own 404 before the container sees them.
    if (req.method === "GET" && req.url === "/health") { res.end("ok"); return; }
    if (req.method === "POST") { void handle(req, res); return; }
    res.statusCode = 404; res.end();
  }).listen(port, () => console.log(`webhook server on :${port}`));
  await bot.api.setWebhook(webhookUrl, { secret_token: secretToken });
  console.log(`webhook set to ${webhookUrl}`);
} else {
  console.log("starting in polling mode");
  void bot.start();
}
