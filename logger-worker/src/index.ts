/**
 * Kargin Archive — usage-logging Cloudflare Worker.
 *
 * The static site (GitHub Pages) sendBeacons anonymous usage events here; this
 * worker inserts them into Neon Postgres via the Neon serverless driver. The
 * DATABASE_URL stays a Worker secret — never in the browser.
 *
 * Deploy:  npm install && npx wrangler deploy
 * Secret:  npx wrangler secret put DATABASE_URL   (paste the Neon connection string)
 * Origin:  set ALLOWED_ORIGIN var in wrangler.toml to your Pages origin.
 */
import { neon } from "@neondatabase/serverless";

interface Env {
  DATABASE_URL: string;
  ALLOWED_ORIGIN?: string;
}

interface LogEvent {
  sessionId?: string;
  type?: string;
  query?: string;
  mode?: string;
  filters?: unknown;
  resultCount?: number;
  sketchId?: string;
  source?: string;
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const cors: Record<string, string> = {
      "Access-Control-Allow-Origin": env.ALLOWED_ORIGIN ?? "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };
    if (req.method === "OPTIONS") return new Response(null, { headers: cors });
    if (req.method !== "POST") return new Response("method not allowed", { status: 405, headers: cors });

    // Body is sent as text/plain (CORS-safelisted, so sendBeacon needs no preflight).
    let events: LogEvent[];
    try {
      const parsed = JSON.parse(await req.text());
      events = (Array.isArray(parsed) ? parsed : [parsed]).slice(0, 50);
    } catch {
      return new Response("bad request", { status: 400, headers: cors });
    }
    if (events.length === 0) return new Response("ok", { headers: cors });

    const ua = req.headers.get("user-agent")?.slice(0, 200) ?? null;
    const sql = neon(env.DATABASE_URL);
    try {
      await sql.transaction(
        events.map((e) => sql`
          insert into query_log
            (session_id, type, query, mode, filters, result_count, sketch_id, source, ua)
          values
            (${e.sessionId ?? ""}, ${e.type ?? "unknown"}, ${e.query ?? null}, ${e.mode ?? null},
             ${e.filters ? JSON.stringify(e.filters) : null}::jsonb, ${e.resultCount ?? null},
             ${e.sketchId ?? null}, ${e.source ?? null}, ${ua})
        `)
      );
    } catch {
      return new Response("db error", { status: 500, headers: cors });
    }
    return new Response("ok", { headers: cors });
  },
};
