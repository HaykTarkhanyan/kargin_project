"use client";
import Link from "next/link";
import { useState } from "react";
import ThemeToggle from "./ThemeToggle";

const NAV = [
  ["/", "Որոնել"], ["/random", "Պատահական"], ["/stats", "Վիճակագրություն"],
  ["/find-my-name", "Իմ անունը"], ["/soundboard", "Ֆրազներ"], ["/quizzes", "Քուիզ"], ["/about", "Մասին"],
] as const;

export default function Header() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-10 border-b-2 border-ink bg-paper">
      <div className="flex items-center justify-between px-4 py-4 sm:px-8">
        <Link href="/" className="flex items-baseline gap-2 text-xl font-extrabold tracking-wide">
          ԿԱՐԳԻՆ<span className="rounded bg-kred px-2 py-0.5 text-[9px] font-extrabold tracking-[0.26em] text-white">ARCHIVE</span>
        </Link>
        <div className="flex items-center gap-3">
          <nav className="hidden gap-4 text-sm font-semibold lg:flex">
            {NAV.map(([href, label]) => (
              <Link key={href} href={href} className="opacity-70 hover:opacity-100">{label}</Link>
            ))}
          </nav>
          <ThemeToggle />
          <button
            className="flex flex-col gap-1.5 p-2 lg:hidden"
            onClick={() => setOpen((o) => !o)}
            aria-label="Ցանկ"
            aria-expanded={open}
          >
            <span className={`block h-0.5 w-6 bg-ink transition-transform ${open ? "translate-y-2 rotate-45" : ""}`} />
            <span className={`block h-0.5 w-6 bg-ink transition-opacity ${open ? "opacity-0" : ""}`} />
            <span className={`block h-0.5 w-6 bg-ink transition-transform ${open ? "-translate-y-2 -rotate-45" : ""}`} />
          </button>
        </div>
      </div>
      {open && (
        <nav className="border-t-2 border-ink bg-paper lg:hidden">
          {NAV.map(([href, label]) => (
            <Link
              key={href}
              href={href}
              onClick={() => setOpen(false)}
              className="block border-b border-ink/20 px-4 py-3 text-sm font-semibold last:border-b-0 hover:bg-paper2"
            >
              {label}
            </Link>
          ))}
        </nav>
      )}
    </header>
  );
}
