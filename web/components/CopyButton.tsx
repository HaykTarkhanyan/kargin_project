"use client";
import { useState } from "react";
import { logEvent } from "@/lib/log";

export default function CopyButton({ label, value, getHref }:
  { label: string; value?: string; getHref?: boolean }) {
  const [done, setDone] = useState(false);
  const onClick = async () => {
    const text = getHref ? window.location.href : (value ?? "");
    try {
      await navigator.clipboard.writeText(text);
      setDone(true); setTimeout(() => setDone(false), 1500);
      logEvent("copy", { source: "watch", query: getHref ? "link" : "quote" });
    } catch {}
  };
  return (
    <button onClick={onClick} className="k-border rounded-lg bg-card px-4 py-2.5 text-sm font-bold hover:bg-ink hover:text-paper">
      {done ? "✓ Պատճենվեց" : label}
    </button>
  );
}
