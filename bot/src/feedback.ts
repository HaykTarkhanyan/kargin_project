/**
 * Visitor reports from Telegram, into the same Firestore `feedback` collection
 * the website writes to (same REST contract, same rules, same caps).
 *
 * Unlike `log.ts` this is awaited and throws: somebody typed a report and is
 * waiting to be told it arrived, so a failure has to reach them.
 *
 * Pseudonymous like the rest of the bot — the Telegram id is hashed, never the
 * username. Anyone wanting a reply is asked to put a contact in their own words,
 * which keeps that a choice rather than something collected by default.
 */
import { createHash } from "node:crypto";

const MESSAGE_MAX = 1000;

export function sessionIdFor(userId: number | undefined): string {
  return userId ? createHash("sha256").update(String(userId)).digest("hex").slice(0, 16) : "anon";
}

export async function sendFeedback(
  userId: number | undefined,
  message: string,
  query: string,
): Promise<void> {
  const pid = process.env.FIREBASE_PROJECT_ID;
  const text = message.trim();
  if (!text) throw new Error("empty message");
  if (!pid) throw new Error("FIREBASE_PROJECT_ID is not set");

  const str = (v: string, max: number) => ({ stringValue: v.slice(0, max) });
  const fields: Record<string, { stringValue: string }> = {
    kind: str("missing", 32),
    message: str(text, MESSAGE_MAX),
    source: str("bot", 32),
    sessionId: str(sessionIdFor(userId), 64),
    ua: str("telegram-bot", 256),
  };
  if (query) fields.query = str(query, 500);

  const docs = `projects/${pid}/databases/(default)/documents`;
  const res = await fetch(`https://firestore.googleapis.com/v1/${docs}:commit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      writes: [{
        update: { name: `${docs}/feedback/${crypto.randomUUID()}`, fields },
        currentDocument: { exists: false },
        updateTransforms: [{ fieldPath: "ts", setToServerValue: "REQUEST_TIME" }],
      }],
    }),
  });
  if (!res.ok) throw new Error(`firestore rejected the report (${res.status})`);
}
