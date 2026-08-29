import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },     // no Image Optimization server on static hosts
  trailingSlash: true,                // friendlier static routing on GitHub Pages
};

export default nextConfig;
