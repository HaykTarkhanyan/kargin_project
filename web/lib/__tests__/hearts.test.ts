import { describe, it, expect, beforeEach, vi } from "vitest";
import { readHearts, toggleHeart, HEARTS_CHANGED } from "@/lib/hearts";
import { logEvent } from "@/lib/log";

vi.mock("@/lib/log", () => ({ logEvent: vi.fn() }));

describe("hearts", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.mocked(logEvent).mockClear();
  });

  it("starts empty and remembers what was hearted", () => {
    expect(readHearts().size).toBe(0);
    expect(toggleHeart("abc", "card")).toBe(true);
    expect([...readHearts()]).toEqual(["abc"]);
  });

  it("toggles back off", () => {
    toggleHeart("abc", "card");
    expect(toggleHeart("abc", "card")).toBe(false);
    expect(readHearts().has("abc")).toBe(false);
  });

  // Counting only the hearts would credit a sketch for a tap somebody took back.
  it("logs both directions, with the sketch and where it came from", () => {
    toggleHeart("abc", "card");
    expect(logEvent).toHaveBeenCalledWith("heart", { sketchId: "abc", source: "card" });
    toggleHeart("abc", "watch");
    expect(logEvent).toHaveBeenCalledWith("unheart", { sketchId: "abc", source: "watch" });
  });

  it("keeps several and does not disturb the others", () => {
    toggleHeart("a", "card");
    toggleHeart("b", "card");
    toggleHeart("a", "card");
    expect([...readHearts()]).toEqual(["b"]);
  });

  it("tells the rest of the page, so every heart for a sketch stays in step", () => {
    const seen = vi.fn();
    window.addEventListener(HEARTS_CHANGED, seen);
    toggleHeart("abc", "card");
    expect(seen).toHaveBeenCalled();
    window.removeEventListener(HEARTS_CHANGED, seen);
  });

  it("survives junk in storage rather than throwing", () => {
    localStorage.setItem("kargin_hearts", "{not json");
    expect(readHearts().size).toBe(0);
    localStorage.setItem("kargin_hearts", JSON.stringify({ nope: true }));
    expect(readHearts().size).toBe(0);
    localStorage.setItem("kargin_hearts", JSON.stringify(["ok", 42, null]));
    expect([...readHearts()]).toEqual(["ok"]);
  });
});
