import type { NextConfig } from "next";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
const config: NextConfig = {
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
