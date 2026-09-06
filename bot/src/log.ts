/**
 * Usage logging into the same Firestore `events` collection the website uses
 * (same REST commit contract as web/lib/log.ts, same firestore.rules limits).
 * source: "bot". Pseudonymous: the Telegram user id is sha256-hashed and
 * truncated — no usernames, no names, nothing reversible stored.
 * No-op until FIREBASE_PROJECT_ID is set. Never throws.
 */
import { createHash } from "node:crypto";

export type BotLogType = "search" | "open";

export function logEvent(
  userId: number | undefined,
  type: BotLogType,
  payload: { query?: string; mode?: string; resultCount?: number; sketchId?: string } = {},
): void {
  const pid = process.env.FIREBASE_PROJECT_ID;
  if (!pid) return;
  const sessionId = userId
    ? createHash("sha256").update(String(userId)).digest("hex").slice(0, 16)
    : "anon";
  const str = (v: string, max: number) => ({ stringValue: v.slice(0, max) });
  const fields: Record<string, { stringValue: string } | { integerValue: string }> = {
    sessionId: str(sessionId, 64),
    type: str(type, 32),
    source: str("bot", 32),
    ua: str("telegram-bot", 256),
  };
  if (payload.query !== undefined) fields.query = str(payload.query, 500);
  if (payload.mode !== undefined) fields.mode = str(payload.mode, 32);
  if (payload.sketchId !== undefined) fields.sketchId = str(payload.sketchId, 64);
  if (payload.resultCount !== undefined)
    fields.resultCount = { integerValue: String(Math.trunc(payload.resultCount)) };

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
  }).catch((e) => console.warn("bot log: flush failed", e));
}
