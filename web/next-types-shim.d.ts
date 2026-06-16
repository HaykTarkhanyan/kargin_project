// Shim for next modules that ship without .d.ts in this custom Next.js 16 build.
// The TypeScript language plugin handles these at IDE time; these shims unblock
// the standalone tsc/build type checker.
declare module "next/types.js" {
  export type ResolvingMetadata = unknown;
  export type ResolvingViewport = unknown;
}
declare module "next/navigation" {
  export function notFound(): never;
  export function redirect(url: string): never;
  export function useRouter(): { push(url: string): void; replace(url: string): void; back(): void; };
  export function useSearchParams(): URLSearchParams;
  export function usePathname(): string;
  export function useParams<T = Record<string, string>>(): T;
}
declare module "next/link" {
  import React from "react";
  const Link: React.FC<React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; prefetch?: boolean }>;
  export default Link;
}
