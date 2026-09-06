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

const MAX_BODY_BYTES = 100_000;   // reject oversized payloads outright
const MAX_FILTERS_CHARS = 2_000;  // drop pathological filter blobs rather than store junk

/** Coerce to a length-bounded string (or null) — keeps an attacker from writing multi-MB rows. */
function clamp(v: unknown, n: number): string | null {
  return typeof v === "string" ? v.slice(0, n) : null;
}

function filtersJson(f: unknown): string | null {
  if (f == null) return null;
  const s = JSON.stringify(f);
  return s.length <= MAX_FILTERS_CHARS ? s : null;
}

function intOrNull(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? Math.trunc(v) : null;
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    // Fail closed: if no ALLOWED_ORIGIN is configured, send no ACAO header so browsers
    // block cross-origin reads. (sendBeacon still delivers — it never reads the response.)
    const allowOrigin = env.ALLOWED_ORIGIN || "";
    const cors: Record<string, string> = {
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
      ...(allowOrigin ? { "Access-Control-Allow-Origin": allowOrigin, "Vary": "Origin" } : {}),
    };
    if (req.method === "OPTIONS") return new Response(null, { headers: cors });
    if (req.method !== "POST") return new Response("method not allowed", { status: 405, headers: cors });

    // Body is sent as text/plain (CORS-safelisted, so sendBeacon needs no preflight).
    const raw = await req.text();
    if (raw.length > MAX_BODY_BYTES) return new Response("payload too large", { status: 413, headers: cors });

    let events: LogEvent[];
    try {
      const parsed = JSON.parse(raw);
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
            (${clamp(e.sessionId, 80) ?? ""}, ${clamp(e.type, 40) ?? "unknown"}, ${clamp(e.query, 500)}, ${clamp(e.mode, 40)},
             ${filtersJson(e.filters)}::jsonb, ${intOrNull(e.resultCount)},
             ${clamp(e.sketchId, 40)}, ${clamp(e.source, 60)}, ${ua})
        `)
      );
    } catch {
      return new Response("db error", { status: 500, headers: cors });
    }
    return new Response("ok", { headers: cors });
  },
};
