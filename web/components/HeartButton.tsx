"use client";
import { useSyncExternalStore } from "react";
import { HEARTS_CHANGED, readHearts, toggleHeart } from "@/lib/hearts";

function subscribe(onChange: () => void) {
  window.addEventListener(HEARTS_CHANGED, onChange);
  return () => window.removeEventListener(HEARTS_CHANGED, onChange);
}

/**
 * One sketch's heart. The state lives in localStorage and is read through
 * useSyncExternalStore: the pages are statically exported, where localStorage
 * does not exist, so the server snapshot is "not hearted" and React swaps in the
 * real value right after hydration without a mismatch. The button keeps no state
 * of its own; toggleHeart announces every change, and that is how it re-renders.
 *
 * On a card this sits ABOVE the stretched link that makes the whole card
 * clickable, so a tap on the heart cannot also navigate away.
 */
export default function HeartButton({
  sketchId, source, size = "sm",
}: {
  sketchId: string;
  source: string;
  size?: "sm" | "lg";
}) {
  const hearted = useSyncExternalStore(subscribe, () => readHearts().has(sketchId), () => false);

  const big = size === "lg";
  return (
    <button
      onClick={() => toggleHeart(sketchId, source)}
      aria-pressed={hearted}
      aria-label={hearted ? "Հանել սիրածներից" : "Ավելացնել սիրածներին"}
      title={hearted ? "Հանել սիրածներից" : "Սիրածներիս մեջ"}
      className={`inline-flex items-center justify-center rounded-full border-2 border-ink transition active:scale-90 ${
        big ? "min-h-11 gap-2 px-4 text-sm font-bold" : "h-9 w-9 text-base"
      } ${hearted ? "bg-kred text-white" : "bg-surface/90 hover:bg-surface"}`}
    >
      <span aria-hidden>{hearted ? "❤️" : "🤍"}</span>
      {big && <span>{hearted ? "Սիրածներումս է" : "Սիրում եմ"}</span>}
    </button>
  );
}
