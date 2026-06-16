/**
 * Anonymous usage logging — batches events and sendBeacons them to the
 * Cloudflare logging Worker (which writes to Neon). No-op until the build sets
 * NEXT_PUBLIC_LOG_ENDPOINT, and on the server (SSR). No personal data.
 */
const ENDPOINT = process.env.NEXT_PUBLIC_LOG_ENDPOINT;

export type LogType = "search" | "open" | "filter" | "findname" | "copy";

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

let queue: LogEvent[] = [];
let timer: ReturnType<typeof setTimeout> | null = null;

function flush(): void {
  timer = null;
  if (!ENDPOINT || queue.length === 0) return;
  const batch = queue.splice(0, 50);
  const body = JSON.stringify(batch);
  try {
    // text/plain keeps it a CORS-simple request (no preflight) for sendBeacon.
    const blob = new Blob([body], { type: "text/plain" });
    if (navigator.sendBeacon && navigator.sendBeacon(ENDPOINT, blob)) return;
    void fetch(ENDPOINT, { method: "POST", body, keepalive: true, headers: { "Content-Type": "text/plain" } });
  } catch {
    /* logging must never break the app */
  }
}

export function logEvent(type: LogType, payload: Omit<LogEvent, "sessionId" | "type"> = {}): void {
  if (!ENDPOINT || typeof window === "undefined") return;
  queue.push({ sessionId: sessionId(), type, ...payload });
  if (!timer) timer = setTimeout(flush, 2000); // batch within 2s
}

if (typeof window !== "undefined") {
  // Flush whatever's queued when the tab is hidden/closed.
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") flush();
  });
}
