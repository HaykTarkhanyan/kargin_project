"use client";
import { useEffect, useState } from "react";

export default function ThemeToggle() {
  const [dark, setDark] = useState(false);
  useEffect(() => { setDark(document.documentElement.classList.contains("dark")); }, []);
  const toggle = () => {
    const next = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", next);
    try { localStorage.setItem("kargin_theme", next ? "dark" : "light"); } catch { /* ignore */ }
    setDark(next);
  };
  return (
    <button onClick={toggle} aria-label="Փոխել թեման" title="Փոխել թեման"
      className="rounded-lg border-2 border-ink px-2 py-1 text-base leading-none hover:bg-ink hover:text-paper">
      {dark ? "☀️" : "🌙"}
    </button>
  );
}
