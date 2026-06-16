import type { NextConfig } from "next";

// Project page = hayktarkhanyan.github.io/kargin_project, so assets live under /kargin_project.
// Apply basePath ONLY for the GitHub Pages build (GITHUB_ACTIONS is set in CI) so local dev/preview stays at root.
// If you switch to a custom domain or a user page (you.github.io), delete this and basePath below.
const isPages = process.env.GITHUB_ACTIONS === "true";

const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },     // no Image Optimization server on static hosts
  trailingSlash: true,                // friendlier static routing on GitHub Pages
  basePath: isPages ? "/kargin_project" : undefined,
};

export default nextConfig;
