# Design: Telegram search bot

Date: 2026-09-07
Status: implemented (code-complete; awaiting BOT_TOKEN from the user)

## Decisions (all made by the user, 2026-09-07)

- **Runtime:** Node/TS + grammY, importing `web/lib/search.ts` directly — one
  search implementation, no drift (the old project's duplicated-search defect).
- **Hosting:** Cloud Run, webhook mode, scale to zero. Polling for local dev.
- **v1 features:** text search with result buttons + paging, inline mode,
  `/random`. (Find-my-name deferred.)
- **Result UX:** `youtu.be` link as the message (Telegram's in-chat player)
  plus a `🌐` button to the canonical watch page.

Full rationale in `DECISIONS.md #8`.

## Shape

```
bot/
├── src/index.ts    entry: BOT_TOKEN required; WEBHOOK_URL ? http server +
│                   setWebhook(secret from token hash) : bot.start() polling
├── src/bot.ts      grammY wiring: /start /help /random, text→search,
│                   callbacks (s:<id> card, r random, m:<off>:<q> paging),
│                   inline_query (empty query = most viewed), chosen_inline_result
├── src/cards.ts    pure builders: card text (HTML-escaped), keyboards,
│                   64-byte callback_data guard — all unit-tested
├── src/data.ts     fs-reads ../web/public/data/sketches.json (kept out of the bundle)
├── src/log.ts      Firestore REST commit, source "bot", sha256(userId)[:16],
│                   no-op without FIREBASE_PROJECT_ID — same rules contract as the site
├── Dockerfile      build from repo root; bundle via esbuild; data baked in
└── README.md       BotFather steps, envs, local dev, Cloud Run deploy
```

- No new Firestore rules needed: bot events use existing types (`search`,
  `open`) and pass the same shape validation.
- Inline queries are NOT logged per keystroke (write-quota hygiene); only
  chosen results are, and only if `/setinlinefeedback` is enabled.
- UI language: Armenian, matching the site.

## Verification

- 10 vitest tests: corpus loads, Armenian⊆Latin search parity through the real
  lib, HTML escaping, paging/keyboard math, 64-byte callback cap.
- `tsc --noEmit` clean (TS 7 native), esbuild bundle builds, and the bundle
  boots to the exact `BOT_TOKEN is required` guard (imports + data load proven).
- Live-chat behavior (webhook, inline sheet) is untestable without the token —
  first smoke test happens when the user supplies credentials.
