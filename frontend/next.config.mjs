/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // En desarrollo con Cloudflare tunnel, el browser no puede llegar a
    // localhost:8000 directamente. El frontend proxea todas las llamadas
    // al backend internamente (container-to-container via API_URL).
    const apiUrl = process.env.API_URL ?? "http://localhost:8000";
    return [
      {
        source: "/api-proxy/:path*",
        destination: `${apiUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
