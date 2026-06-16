import Link from "next/link";

const NAV = [
  ["/", "Որոնել"], ["/random", "Պատահական"], ["/about", "Մասին"],
] as const;

export default function Header() {
  return (
    <header className="sticky top-0 z-10 flex items-center justify-between border-b-2 border-ink bg-paper px-8 py-4">
      <Link href="/" className="flex items-baseline gap-2 text-xl font-extrabold tracking-wide">
        ԿԱՐԳԻՆ<span className="rounded bg-kred px-2 py-0.5 text-[9px] font-extrabold tracking-[0.26em] text-white">ARCHIVE</span>
      </Link>
      <nav className="flex gap-6 text-sm font-semibold">
        {NAV.map(([href, label]) => (
          <Link key={href} href={href} className="opacity-70 hover:opacity-100">{label}</Link>
        ))}
      </nav>
    </header>
  );
}
