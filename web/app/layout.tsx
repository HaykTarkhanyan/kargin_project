import type { Metadata } from "next";
import { Anton, Inter, Noto_Sans_Armenian } from "next/font/google";
import "./globals.css";
import Header from "@/components/Header";

const anton = Anton({ weight: "400", subsets: ["latin"], variable: "--font-anton" });
const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const arm = Noto_Sans_Armenian({ subsets: ["armenian"], weight: ["400", "600", "700", "800"], variable: "--font-arm" });

export const metadata: Metadata = {
  title: "Կարգին Արխիվ — Kargin Archive",
  description: "Որոնիր 702 Կարգին սքեթչ՝ տող առ տող։",
};

// Apply the saved theme before paint to avoid a flash.
const THEME_INIT = `try{if(localStorage.getItem('kargin_theme')==='dark')document.documentElement.classList.add('dark')}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="hy" suppressHydrationWarning className={`${anton.variable} ${inter.variable} ${arm.variable}`}>
      <body>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT }} />
        <Header />{children}
      </body>
    </html>
  );
}
