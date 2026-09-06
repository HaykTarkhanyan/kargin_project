import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import ShareButton from "@/components/ShareButton";

const URL_ = "https://karginhaghordum.am/sketch/abc123/";
const TITLE = "Կարգին սքեթչ";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  // jsdom has no navigator.share by default; remove any stub a test added.
  delete (navigator as { share?: unknown }).share;
});

describe("ShareButton", () => {
  it("uses the native share sheet when navigator.share exists", () => {
    const share = vi.fn().mockResolvedValue(undefined);
    (navigator as { share?: unknown }).share = share;
    render(<ShareButton url={URL_} title={TITLE} />);
    fireEvent.click(screen.getByText("📤 Կիսվել"));
    expect(share).toHaveBeenCalledWith({ title: TITLE, url: URL_ });
    expect(screen.queryByText("Telegram")).toBeNull(); // no dropdown on the native path
  });

  it("opens a dropdown with encoded Telegram/WhatsApp/Facebook links otherwise", () => {
    render(<ShareButton url={URL_} title={TITLE} />);
    fireEvent.click(screen.getByText("📤 Կիսվել"));
    const enc = encodeURIComponent(URL_);
    expect(screen.getByText("Telegram").getAttribute("href")).toBe(
      `https://t.me/share/url?url=${enc}&text=${encodeURIComponent(TITLE)}`,
    );
    expect(screen.getByText("WhatsApp").getAttribute("href")).toBe(
      `https://wa.me/?text=${encodeURIComponent(`${TITLE} ${URL_}`)}`,
    );
    expect(screen.getByText("Facebook").getAttribute("href")).toBe(
      `https://www.facebook.com/sharer/sharer.php?u=${enc}`,
    );
  });

  it("copies the canonical link from the dropdown fallback item", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { ...navigator, clipboard: { writeText } });
    render(<ShareButton url={URL_} title={TITLE} />);
    fireEvent.click(screen.getByText("📤 Կիսվել"));
    fireEvent.click(screen.getByText("🔗 Պատճենել հղումը"));
    expect(writeText).toHaveBeenCalledWith(URL_);
    expect(await screen.findByText("✓ Պատճենվեց")).toBeTruthy();
  });
});
