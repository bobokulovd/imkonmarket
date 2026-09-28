/** @type {import('next').NextConfig} */
// Brauzer so'rovlari /api, /media, /admin, /static — shu domen orqali backendga proksi qilinadi.
// BACKEND_URL build vaqtida o'qiladi (Docker Compose ichida: http://backend:8000).
const BACKEND = (process.env.BACKEND_URL || "http://localhost:8000").replace(/\/$/, "");

const nextConfig = {
  output: "standalone",
  images: { unoptimized: true },
  async rewrites() {
    return [
      // Django URL'lari "/" bilan tugaydi — slashni saqlab uzatamiz
      { source: "/api/:path*/", destination: `${BACKEND}/api/:path*/` },
      { source: "/api/:path*", destination: `${BACKEND}/api/:path*` },
      { source: "/media/:path*", destination: `${BACKEND}/media/:path*` },
      { source: "/admin", destination: `${BACKEND}/admin/` },
      { source: "/admin/:path*/", destination: `${BACKEND}/admin/:path*/` },
      { source: "/admin/:path*", destination: `${BACKEND}/admin/:path*` },
      { source: "/static/:path*", destination: `${BACKEND}/static/:path*` },
    ];
  },
  skipTrailingSlashRedirect: true,
};
export default nextConfig;
