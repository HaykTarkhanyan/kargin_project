# Kargin Archive — usage logging (Cloudflare Worker + Neon)

The static site can't hold a DB credential, so anonymous usage events are POSTed to this tiny Worker, which inserts them into Neon Postgres. Logging is **off** on the site until you set the Worker URL (step 5).

## One-time setup

### 1. Create a Neon project + table
- Sign up at https://neon.tech (free), create a project. Copy the **connection string** (`postgresql://...`).
- In the Neon **SQL Editor**, run [`schema.sql`](./schema.sql) to create the `query_log` table.

### 2. Deploy the Worker
```bash
cd logger-worker
npm install
npx wrangler login                       # opens browser, one-time
npx wrangler secret put DATABASE_URL     # paste the Neon connection string
npx wrangler deploy                      # prints your Worker URL, e.g. https://kargin-logger.<you>.workers.dev
```
(Confirm `ALLOWED_ORIGIN` in `wrangler.toml` matches your site origin: `https://hayktarkhanyan.github.io`.)

### 3. Smoke-test the Worker
```bash
curl -X POST https://kargin-logger.<you>.workers.dev \
  -H "Content-Type: text/plain" \
  -d '[{"sessionId":"test","type":"search","query":"тест","resultCount":3,"source":"home"}]'
# → "ok", and the row appears in Neon
```

### 4. Turn logging on for the site
Add the Worker URL as a **repo variable** so the build bakes it in:
- GitHub → repo **Settings → Secrets and variables → Actions → Variables → New variable**
- Name: `LOG_ENDPOINT`  Value: `https://kargin-logger.<you>.workers.dev`

### 5. Redeploy the site
Push any commit (or re-run the Pages workflow). The build reads `LOG_ENDPOINT` and `lib/log.ts` starts sending events. Until `LOG_ENDPOINT` is set, logging is a silent no-op.

## What's logged
Anonymous only: a random per-tab `session_id`, the event `type` (search / open / filter / findname / copy), the query text, result count, sketch id, applied filters, and a coarse user-agent. No accounts, no IP stored, no personal data. See the example analytics queries at the bottom of `schema.sql`.
