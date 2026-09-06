"use client";
import { useState } from "react";
import { logEvent } from "@/lib/log";

export default function CopyButton({ label, value, getHref, compact }:
  { label: string; value?: string; getHref?: boolean; compact?: boolean }) {
  const [done, setDone] = useState(false);
  const onClick = async () => {
    const text = getHref ? window.location.href : (value ?? "");
    try {
      await navigator.clipboard.writeText(text);
      setDone(true); setTimeout(() => setDone(false), 1500);
      logEvent("copy", { source: "watch", query: getHref ? "link" : "quote" });
    } catch {}
  };
  if (compact) {
    return (
      <button onClick={onClick} title={label} aria-label={label}
        className="shrink-0 rounded-md border-2 border-ink bg-card px-1.5 py-0.5 text-xs font-bold leading-none hover:bg-ink hover:text-paper">
        {done ? "✓" : "📋"}
      </button>
    );
  }
  return (
    <button onClick={onClick} className="k-border rounded-lg bg-card px-4 py-2.5 text-sm font-bold hover:bg-ink hover:text-paper">
      {done ? "✓ Պատճենվեց" : label}
    </button>
  );
}
