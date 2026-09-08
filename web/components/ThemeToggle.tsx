"use client";
import { useState } from "react";

export default function ThemeToggle() {
  // Read the theme that layout.tsx's inline script set pre-paint, so the icon is correct
  // on the first client render (no post-mount flash). suppressHydrationWarning covers the
  // expected server(🌙)/client mismatch under static export.
  const [dark, setDark] = useState(() =>
    typeof document !== "undefined" && document.documentElement.classList.contains("dark"));
  const toggle = () => {
    const next = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", next);
    try { localStorage.setItem("kargin_theme", next ? "dark" : "light"); } catch { /* ignore */ }
    setDark(next);
  };
  return (
    <button onClick={toggle} aria-label="Փոխել թեման" title="Փոխել թեման" suppressHydrationWarning
      className="flex h-11 w-11 items-center justify-center rounded-lg border-2 border-ink text-base leading-none hover:bg-ink hover:text-paper sm:h-9 sm:w-11">
      {dark ? "☀️" : "🌙"}
    </button>
  );
}
