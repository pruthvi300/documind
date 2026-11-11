/** @type {import('next').NextConfig} */
const API_URL = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const nextConfig = {
  reactStrictMode: true,
  // The browser calls same-origin /api/*; Next.js forwards it to FastAPI, so no CORS is needed.
  async rewrites() {
    return [{ source: '/api/:path*', destination: `${API_URL}/api/:path*` }];
  },
};

module.exports = nextConfig;
