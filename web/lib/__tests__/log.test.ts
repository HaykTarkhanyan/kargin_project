import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const PROJECT = "kargin-test";
const url = (calls: ReturnType<typeof vi.fn>["mock"]["calls"]) => calls[0][0] as string;
const body = (calls: ReturnType<typeof vi.fn>["mock"]["calls"]) =>
  JSON.parse((calls[0][1] as RequestInit).body as string);

let fetchMock: ReturnType<typeof vi.fn>;

async function freshLog(projectId: string) {
  vi.resetModules();
  vi.stubEnv("NEXT_PUBLIC_FIREBASE_PROJECT_ID", projectId); // "" = unset (falsy), never leaks the real env
  return await import("../log");
}

beforeEach(() => {
  vi.useFakeTimers();
  fetchMock = vi.fn().mockResolvedValue({ ok: true });
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("log transport", () => {
  it("is a no-op when NEXT_PUBLIC_FIREBASE_PROJECT_ID is unset", async () => {
    const { logEvent } = await freshLog("");
    logEvent("search", { query: "q" });
    vi.advanceTimersByTime(3000);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("batches events within 2s into one commit with keepalive", async () => {
    const { logEvent } = await freshLog(PROJECT);
    logEvent("search", { query: "բարեւ", resultCount: 3, source: "home" });
    logEvent("open", { sketchId: "abc123" });
    vi.advanceTimersByTime(2100);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(url(fetchMock.mock.calls)).toBe(
      `https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents:commit`,
    );
    expect((fetchMock.mock.calls[0][1] as RequestInit).keepalive).toBe(true);
    const writes = body(fetchMock.mock.calls).writes;
    expect(writes).toHaveLength(2);
    expect(writes[0].update.name).toMatch(
      new RegExp(`^projects/${PROJECT}/databases/\\(default\\)/documents/events/[0-9a-f-]{36}$`),
    );
    expect(writes[0].currentDocument).toEqual({ exists: false });
    expect(writes[0].updateTransforms).toEqual([{ fieldPath: "ts", setToServerValue: "REQUEST_TIME" }]);
    const f = writes[0].update.fields;
    expect(f.type).toEqual({ stringValue: "search" });
    expect(f.query).toEqual({ stringValue: "բարեւ" });
    expect(f.resultCount).toEqual({ integerValue: "3" });
    expect(f.sessionId.stringValue.length).toBeGreaterThan(0);
    expect(f.ua.stringValue.length).toBeLessThanOrEqual(256);
    expect(f.ts).toBeUndefined(); // ts comes only from the server transform
  });

  it("clamps oversized fields to the rules contract", async () => {
    const { logEvent } = await freshLog(PROJECT);
    logEvent("search", { query: "x".repeat(600), filters: { loc: ["y".repeat(2000)] } });
    vi.advanceTimersByTime(2100);
    const f = body(fetchMock.mock.calls).writes[0].update.fields;
    expect(f.query.stringValue).toHaveLength(500);
    expect(typeof f.filters.stringValue).toBe("string"); // filters is a JSON string by contract
    expect(f.filters.stringValue.length).toBeLessThanOrEqual(1000);
  });

  it("drops undefined fields instead of encoding them", async () => {
    const { logEvent } = await freshLog(PROJECT);
    logEvent("copy", { sketchId: "abc" });
    vi.advanceTimersByTime(2100);
    const f = body(fetchMock.mock.calls).writes[0].update.fields;
    expect(f.query).toBeUndefined();
    expect(f.filters).toBeUndefined();
  });

  it("never throws when fetch fails", async () => {
    fetchMock.mockRejectedValue(new Error("network down"));
    const { logEvent } = await freshLog(PROJECT);
    expect(() => {
      logEvent("search", { query: "q" });
      vi.advanceTimersByTime(2100);
    }).not.toThrow();
  });
});
