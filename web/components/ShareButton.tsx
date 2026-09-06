"use client";
import { useState } from "react";
import { logEvent } from "@/lib/log";

/**
 * Share a sketch. Mobile browsers get the native share sheet (navigator.share);
 * everywhere else a small dropdown offers Telegram / WhatsApp / Facebook plus
 * copy-link. Links always point at the canonical domain, whatever host the
 * visitor happens to be on.
 */
export default function ShareButton({ url, title }: { url: string; title: string }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const onClick = async () => {
    if (typeof navigator.share === "function") {
      try {
        await navigator.share({ title, url });
        logEvent("share", { source: "watch", query: "native" });
      } catch {} // user closed the sheet — not an error
      return;
    }
    setOpen((v) => !v);
  };

  const targets = [
    { name: "Telegram", href: `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(title)}` },
    { name: "WhatsApp", href: `https://wa.me/?text=${encodeURIComponent(`${title} ${url}`)}` },
    { name: "Facebook", href: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}` },
  ];

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true); setTimeout(() => setCopied(false), 1500);
      logEvent("copy", { source: "watch", query: "link" });
    } catch {}
  };

  return (
    <div className="relative">
      <button onClick={onClick} className="k-border rounded-lg bg-card px-4 py-2.5 text-sm font-bold hover:bg-ink hover:text-paper">
        📤 Կիսվել
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-full z-20 mt-1.5 w-44 overflow-hidden rounded-lg border-2 border-ink bg-surface k-shadow">
            {targets.map((t) => (
              <a key={t.name} href={t.href} target="_blank" rel="noreferrer"
                onClick={() => { logEvent("share", { source: "watch", query: t.name.toLowerCase() }); setOpen(false); }}
                className="block px-3 py-2 text-sm font-bold hover:bg-ink hover:text-paper">
                {t.name}
              </a>
            ))}
            <button onClick={copyLink}
              className="block w-full border-t-2 border-ink px-3 py-2 text-left text-sm font-bold hover:bg-ink hover:text-paper">
              {copied ? "✓ Պատճենվեց" : "🔗 Պատճենել հղումը"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
