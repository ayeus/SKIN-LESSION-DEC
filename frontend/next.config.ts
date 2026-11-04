import type { NextConfig } from "next";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
const config: NextConfig = {
  devIndicators: false,
  distDir: process.env.DERMA_E2E === "1" ? ".next-e2e" : ".next",
  turbopack: { root: dirname(fileURLToPath(import.meta.url)) },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.API_URL || "http://127.0.0.1:8000"}/:path*`,
      },
    ];
  },
};
export default config;
