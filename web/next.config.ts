import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },     // no Image Optimization server on static hosts
  // basePath/assetPrefix: set ONLY for a project page (user.github.io/<repo>) — decided in deploy task
  trailingSlash: true,                // friendlier static routing on GitHub Pages
};

export default nextConfig;
