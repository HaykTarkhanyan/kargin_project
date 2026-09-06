/**
 * Anonymous usage logging — batches events and writes them straight to
 * Firestore's REST commit endpoint with fetch(keepalive). No SDK: security
 * lives in firestore.rules (create-only, shape-validated), and keepalive
 * preserves delivery when the tab closes. No-op until the build sets
 * NEXT_PUBLIC_FIREBASE_PROJECT_ID, and on the server (SSR). No personal data.
 * Clamps mirror the rules contract — a rules rejection means a bug, and the
 * whole batch is dropped with a console.warn (fine for telemetry).
 */
export type LogType = "search" | "open" | "filter" | "findname" | "copy" | "share";

interface LogEvent {
  sessionId: string;
  type: LogType;
  query?: string;
  mode?: string;
  filters?: unknown;
  resultCount?: number;
  sketchId?: string;
  source?: string;
}

function projectId(): string | undefined {
  return process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID;
}

function sessionId(): string {
  try {
    let id = sessionStorage.getItem("kargin_sid");
    if (!id) {
      id = crypto.randomUUID();
      sessionStorage.setItem("kargin_sid", id);
    }
    return id;
  } catch (e) {
    console.warn("kargin log: sessionId unavailable", e);
    return "anon";
  }
}

type FsValue = { stringValue: string } | { integerValue: string };

/** Clamp to the firestore.rules contract and encode as Firestore REST values. */
function toFields(e: LogEvent): Record<string, FsValue> {
  const s = (v: string, max: number): FsValue => ({ stringValue: v.slice(0, max) });
  const fields: Record<string, FsValue> = {
    sessionId: s(e.sessionId, 64),
    type: s(e.type, 32),
    ua: s(navigator.userAgent, 256),
  };
  if (e.query !== undefined) fields.query = s(e.query, 500);
  if (e.mode !== undefined) fields.mode = s(e.mode, 32);
  if (e.filters !== undefined) fields.filters = s(JSON.stringify(e.filters), 1000);
  if (e.resultCount !== undefined)
    // Always an integer: rules require `is int`, and one float would fail the whole batch.
    fields.resultCount = { integerValue: String(Math.trunc(e.resultCount)) };
  if (e.sketchId !== undefined) fields.sketchId = s(e.sketchId, 64);
  if (e.source !== undefined) fields.source = s(e.source, 32);
  return fields;
}

const queue: LogEvent[] = [];
let timer: ReturnType<typeof setTimeout> | null = null;

function flush(): void {
  timer = null;
  const pid = projectId();
  if (!pid || queue.length === 0) return;
  // 20 events × ~2 KB worst-case clamped fields ≈ 40 KB — keepalive bodies cap at 64 KB.
  const batch = queue.splice(0, 20);
  const docs = `projects/${pid}/databases/(default)/documents`;
  const writes = batch.map((e) => ({
    update: { name: `${docs}/events/${crypto.randomUUID()}`, fields: toFields(e) },
    currentDocument: { exists: false },
    updateTransforms: [{ fieldPath: "ts", setToServerValue: "REQUEST_TIME" }],
  }));
  try {
    void fetch(`https://firestore.googleapis.com/v1/${docs}:commit`, {
      method: "POST",
      body: JSON.stringify({ writes }),
      keepalive: true,
      headers: { "Content-Type": "application/json" },
    }).catch((e) => console.warn("kargin log: flush failed", e));
  } catch (e) {
    /* logging must never break the app, but the failure must be observable */
    console.warn("kargin log: flush failed", e);
  }
}

export function logEvent(type: LogType, payload: Omit<LogEvent, "sessionId" | "type"> = {}): void {
  if (!projectId() || typeof window === "undefined") return;
  queue.push({ sessionId: sessionId(), type, ...payload });
  if (!timer) timer = setTimeout(flush, 2000); // batch within 2s
}

if (typeof window !== "undefined") {
  // Flush whatever's queued when the tab is hidden/closed.
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") flush();
  });
}
