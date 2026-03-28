import type { NextConfig } from "next";

function normalizeProxyTarget(rawTarget?: string) {
  if (!rawTarget) {
    return "";
  }
  const target = rawTarget.startsWith("http://") || rawTarget.startsWith("https://")
    ? rawTarget
    : `http://${rawTarget}`;
  return target.endsWith("/") ? target.slice(0, -1) : target;
}

const nextConfig: NextConfig = {
  reactStrictMode: true,
  distDir: ".next-build",
  async rewrites() {
    const proxyTarget = normalizeProxyTarget(
      process.env.CK_V2_INTERNAL_API_BASE_URL ?? process.env.CK_V2_INTERNAL_API_HOSTPORT,
    );
    if (!proxyTarget) {
      return [];
    }
    return [
      {
        source: "/v2-api/:path*",
        destination: `${proxyTarget}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
