/**
 * Visitor reports — a sketch the archive is missing, or a mistake in one.
 *
 * Same transport as `log.ts` (Firestore's REST commit endpoint, no SDK, rules as
 * the only backend) but deliberately NOT fire-and-forget: somebody typed this and
 * is waiting to hear it landed, so the call is awaited and failure is surfaced
 * rather than swallowed. Clamps mirror `firestore.rules`; a rules rejection here
 * means the two drifted apart.
 */

export type FeedbackKind = "missing" | "wrong";

export interface Feedback {
  kind: FeedbackKind;
  /** What the visitor wrote. The only required field. */
  message: string;
  /** The search that failed them, when there was one. */
  query?: string;
  /** The sketch being corrected, for a report sent from a watch page. */
  sketchId?: string;
  /** Optional, so Hayk can reply. Free text — email, phone or Telegram handle. */
  contact?: string;
  source?: string;
}

export const MESSAGE_MAX = 1000;
export const CONTACT_MAX = 200;

type FsValue = { stringValue: string };

function sessionId(): string {
  try {
    let id = sessionStorage.getItem("kargin_sid");
    if (!id) {
      id = crypto.randomUUID();
      sessionStorage.setItem("kargin_sid", id);
    }
    return id;
  } catch {
    return "anon";
  }
}

/** Clamp to the rules contract and encode as Firestore REST values. */
export function toFields(f: Feedback, session: string, ua: string): Record<string, FsValue> {
  const s = (v: string, max: number): FsValue => ({ stringValue: v.slice(0, max) });
  const fields: Record<string, FsValue> = {
    kind: s(f.kind, 32),
    message: s(f.message.trim(), MESSAGE_MAX),
    sessionId: s(session, 64),
    ua: s(ua, 256),
  };
  if (f.query) fields.query = s(f.query, 500);
  if (f.sketchId) fields.sketchId = s(f.sketchId, 64);
  if (f.contact) fields.contact = s(f.contact.trim(), CONTACT_MAX);
  if (f.source) fields.source = s(f.source, 32);
  return fields;
}

/**
 * Send one report. Resolves when Firestore has it; throws otherwise, so the form
 * can tell the visitor it did not go through instead of pretending it did.
 */
export async function submitFeedback(f: Feedback): Promise<void> {
  const pid = process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID;
  if (!pid) throw new Error("feedback is not configured (no NEXT_PUBLIC_FIREBASE_PROJECT_ID)");
  if (!f.message.trim()) throw new Error("empty message");

  const docs = `projects/${pid}/databases/(default)/documents`;
  const res = await fetch(`https://firestore.googleapis.com/v1/${docs}:commit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      writes: [{
        update: { name: `${docs}/feedback/${crypto.randomUUID()}`, fields: toFields(f, sessionId(), navigator.userAgent) },
        currentDocument: { exists: false },
        updateTransforms: [{ fieldPath: "ts", setToServerValue: "REQUEST_TIME" }],
      }],
    }),
  });
  if (!res.ok) throw new Error(`feedback rejected (${res.status})`);
}
