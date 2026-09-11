# Kargin Archive — Telegram bot

Search the sketch archive from Telegram. Same search as the website — it imports
`web/lib/search.ts` directly (transliteration, Cyrillic, fuzzy), so results never
drift between the two surfaces.

**Features:** text search with tappable results and paging · inline mode
(`@bot <query>` in any chat drops a sketch card into the conversation) ·
`/random` · results open as a `youtu.be` link (plays inside Telegram) with a
button to the `karginhaghordum.am` watch page · `/feedback` and a button on the
no-results message for reporting a sketch we are missing · anonymous usage
logging into the same Firestore `events` collection as the site (source `bot`,
hashed user ids, off until configured).

Reports are sent with `force_reply` and recognised by the prompt's own first
character, so nothing about "who is mid-report" is held in memory — the service
scales to zero between messages, and anything kept there would be gone. They land
in the `feedback` collection alongside the website's; read them with
`scripts/non_essential/report_usage.py`.

## One-time BotFather setup

1. Message [@BotFather](https://t.me/BotFather): `/newbot` → pick a name and a
   username → copy the **token**.
2. `/setinline` → select the bot → set a placeholder like `փնտրիր սքեթչ…`
   (this is what enables inline mode).
3. Optional, for analytics on inline shares: `/setinlinefeedback` → **Enabled**.
   Without it inline shares simply go unlogged; everything else works.
4. Commands (`/random`, `/help`) are registered automatically at boot.

## Environment

| var | required | meaning |
|---|---|---|
| `BOT_TOKEN` | yes | from BotFather |
| `WEBHOOK_URL` | no | public HTTPS URL of the service; set → webhook mode, unset → long polling |
| `PORT` | no | webhook server port (Cloud Run injects it; default 8080) |
| `FIREBASE_PROJECT_ID` | no | enables usage logging to Firestore `events` |

## Local development (polling — no public URL needed)

```bash
cd bot
npm ci
BOT_TOKEN=123:abc npm run dev     # tsx watch; Ctrl+C to stop
npm test                          # unit tests (search parity, cards, keyboards)
npm run typecheck
```

Note: switching a bot from webhook back to polling requires deleting the
webhook once: `curl "https://api.telegram.org/bot<TOKEN>/deleteWebhook"`.

## Deploy to Cloud Run

```bash
uv run python scripts/deploy_bot.py v4     # bump the tag every time
```

That builds on **Cloud Build** and repoints the service — nothing is built
locally, so it needs neither Docker Desktop nor gcloud, and it will not tie up
the machine. Auth is the firebase CLI's existing login. Env vars (`BOT_TOKEN`,
`WEBHOOK_URL`, `FIREBASE_PROJECT_ID`) are read back and re-sent unchanged, so a
deploy never drops them.

Check it afterwards:

```bash
curl https://kargin-bot-<hash>-ey.a.run.app/health           # -> ok
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"    # -> 0 pending, no last_error
```

A build must name a service account: the legacy
`<number>@cloudbuild.gserviceaccount.com` is still in the IAM policy but Google
no longer creates it, and omitting `serviceAccount` fails with a bare "caller
does not have permission". The script passes the compute default explicitly.

The bot registers its own webhook (with a secret token derived from
`BOT_TOKEN`) on boot, so no manual `setWebhook` call is needed. `GET /health`
answers `ok` for liveness checks (not `/healthz` — Google's frontend reserves
z-suffixed paths on `run.app` URLs and 404s them itself). Data updates ship by rebuilding the image —
`sketches.json` is baked in, same artifact the website uses.
