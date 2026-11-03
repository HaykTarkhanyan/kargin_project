# Next.js static export → GitHub Pages *project page* needs `basePath = "/<repo>"`

*From LEARNINGS.md, section "Website MVP — frontend & deploy (2026-06-16)".*

**Next.js static export → GitHub Pages *project page* needs `basePath = "/<repo>"`.** Gate it on `process.env.GITHUB_ACTIONS === "true"` so local dev/preview stays at root. Intercepting/parallel-route modals do NOT survive `output: 'export'` — ship plain `/sketch/[id]` pages (deep-linkable + shareable) instead of a modal overlay.
