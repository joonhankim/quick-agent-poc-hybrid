import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/agent/:path*',
        destination: 'http://localhost:8000/agent/:path*',
      },
      {
        source: '/db/:path*',
        destination: 'http://localhost:8000/db/:path*',
      },
    ];
  },
};

export default nextConfig;
