/**
 * Usage logging. Two sinks, picked automatically:
 *   - FIREBASE_PROJECT_ID set → the shared Firestore `events` collection (same
 *     REST commit contract and rules limits as web/lib/log.ts), source "bot".
 *   - otherwise → logs/bot_events.jsonl at the repo root, one JSON per line,
 *     so usage is captured even before the Firebase project exists. The file
 *     can be backfilled into Firestore later if ever wanted.
 * Pseudonymous either way: the Telegram user id is sha256-hashed and truncated —
 * no usernames, no names, nothing reversible stored. Never throws.
 */
import { createHash } from "node:crypto";
import { appendFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const LOCAL_LOG = join(here, "..", "..", "logs", "bot_events.jsonl");

export type BotLogType = "search" | "open";

interface Payload { query?: string; mode?: string; resultCount?: number; sketchId?: string }

function toFirestore(pid: string, sessionId: string, type: BotLogType, p: Payload): void {
  const str = (v: string, max: number) => ({ stringValue: v.slice(0, max) });
  const fields: Record<string, { stringValue: string } | { integerValue: string }> = {
    sessionId: str(sessionId, 64),
    type: str(type, 32),
    source: str("bot", 32),
    ua: str("telegram-bot", 256),
  };
  if (p.query !== undefined) fields.query = str(p.query, 500);
  if (p.mode !== undefined) fields.mode = str(p.mode, 32);
  if (p.sketchId !== undefined) fields.sketchId = str(p.sketchId, 64);
  if (p.resultCount !== undefined)
    fields.resultCount = { integerValue: String(Math.trunc(p.resultCount)) };

  const docs = `projects/${pid}/databases/(default)/documents`;
  fetch(`https://firestore.googleapis.com/v1/${docs}:commit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      writes: [{
        update: { name: `${docs}/events/${crypto.randomUUID()}`, fields },
        currentDocument: { exists: false },
        updateTransforms: [{ fieldPath: "ts", setToServerValue: "REQUEST_TIME" }],
      }],
    }),
  }).catch((e) => console.warn("bot log: firestore flush failed", e));
}

function toLocalFile(sessionId: string, type: BotLogType, p: Payload): void {
  try {
    mkdirSync(dirname(LOCAL_LOG), { recursive: true });
    appendFileSync(
      LOCAL_LOG,
      `${JSON.stringify({ ts: new Date().toISOString(), sessionId, type, source: "bot", ...p })}\n`,
    );
  } catch (e) {
    console.warn("bot log: local sink failed", e);
  }
}

export function logEvent(userId: number | undefined, type: BotLogType, payload: Payload = {}): void {
  const sessionId = userId
    ? createHash("sha256").update(String(userId)).digest("hex").slice(0, 16)
    : "anon";
  const pid = process.env.FIREBASE_PROJECT_ID;
  if (pid) toFirestore(pid, sessionId, type, payload);
  else toLocalFile(sessionId, type, payload);
}
