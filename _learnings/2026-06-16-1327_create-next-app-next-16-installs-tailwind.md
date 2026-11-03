# `create-next-app` (Next 16) installs Tailwind v4, which is CSS-first — there is NO `tailwind.config.ts`

*From LEARNINGS.md, section "Website MVP — frontend & deploy (2026-06-16)".*

**`create-next-app` (Next 16) installs Tailwind v4, which is CSS-first — there is NO `tailwind.config.ts`.** Theming lives in `web/app/globals.css` via `@import "tailwindcss"` + `@theme inline` (declare `--color-*`, `--font-*`, which generate `bg-*`/`text-*`/`font-*` utilities). A plan that `git add`s a `tailwind.config.ts` hard-fails the commit. Verify the installed Tailwind major before assuming v3 syntax.
