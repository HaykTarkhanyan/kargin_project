import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import HeartButton from "@/components/HeartButton";

vi.mock("@/lib/log", () => ({ logEvent: vi.fn() }));

describe("HeartButton", () => {
  beforeEach(() => localStorage.clear());

  // The button keeps no state of its own: it re-reads storage when toggleHeart
  // announces a change, so a missed announcement would leave it stuck.
  it("flips when tapped, and back", () => {
    render(<HeartButton sketchId="abc" source="card" />);
    const btn = screen.getByRole("button");
    expect(btn.getAttribute("aria-pressed")).toBe("false");
    fireEvent.click(btn);
    expect(btn.getAttribute("aria-pressed")).toBe("true");
    fireEvent.click(btn);
    expect(btn.getAttribute("aria-pressed")).toBe("false");
  });

  it("shows a heart saved on an earlier visit", () => {
    localStorage.setItem("kargin_hearts", JSON.stringify(["abc"]));
    render(<HeartButton sketchId="abc" source="card" />);
    expect(screen.getByRole("button").getAttribute("aria-pressed")).toBe("true");
  });
});
