# Kargin Archive — Telegram bot

Search the sketch archive from Telegram. Same search as the website — it imports
`web/lib/search.ts` directly (transliteration, Cyrillic, fuzzy), so results never
drift between the two surfaces.

**Features:** text search with tappable results and paging · inline mode
(`@bot <query>` in any chat drops a sketch card into the conversation) ·
`/random` · results open as a `youtu.be` link (plays inside Telegram) with a
button to the `karginhaghordum.am` watch page · anonymous usage logging into the
same Firestore `events` collection as the site (source `bot`, hashed user ids,
off until configured).

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
# from the REPO ROOT
docker build -f bot/Dockerfile -t europe-west3-docker.pkg.dev/<PROJECT>/bots/kargin-bot .
docker push europe-west3-docker.pkg.dev/<PROJECT>/bots/kargin-bot

gcloud run deploy kargin-bot \
  --image europe-west3-docker.pkg.dev/<PROJECT>/bots/kargin-bot \
  --region europe-west3 --allow-unauthenticated --min-instances 0 \
  --set-secrets BOT_TOKEN=kargin-bot-token:latest \
  --set-env-vars FIREBASE_PROJECT_ID=<PROJECT>

# first deploy prints the service URL; wire the webhook by redeploying with it:
gcloud run services update kargin-bot --region europe-west3 \
  --set-env-vars WEBHOOK_URL=https://kargin-bot-<hash>-ey.a.run.app,FIREBASE_PROJECT_ID=<PROJECT>
```

The bot registers its own webhook (with a secret token derived from
`BOT_TOKEN`) on boot, so no manual `setWebhook` call is needed. `GET /healthz`
answers `ok` for liveness checks. Data updates ship by rebuilding the image —
`sketches.json` is baked in, same artifact the website uses.
