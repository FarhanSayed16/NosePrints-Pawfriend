import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import basicSsl from "@vitejs/plugin-basic-ssl";

const apiProxy = {
  "/api/v1": { target: "http://127.0.0.1:8000", changeOrigin: true },
  "/uploads": { target: "http://127.0.0.1:8000", changeOrigin: true },
  "/health": { target: "http://127.0.0.1:8000", changeOrigin: true },
};

// `npm run tunnel` = HTTP production preview for Cloudflare (public URL is already HTTPS).
// `npm run dev` = self-signed HTTPS for camera on LAN IPs.
const forTunnel = process.env.npm_lifecycle_event === "tunnel";

function noStoreHtml() {
  const setHeaders = (req, res, next) => {
    const url = req.url?.split("?")[0] || "";
    if (url === "/" || url === "/index.html" || url === "/sw.js" || url === "/manifest.json") {
      res.setHeader("Cache-Control", "no-store, no-cache, must-revalidate");
    }
    next();
  };
  return {
    name: "no-store-html",
    configureServer(server) {
      server.middlewares.use(setHeaders);
    },
    configurePreviewServer(server) {
      server.middlewares.use(setHeaders);
    },
  };
}

export default defineConfig({
  plugins: [react(), noStoreHtml(), ...(forTunnel ? [] : [basicSsl()])],
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    allowedHosts: true,
    proxy: apiProxy,
  },
  preview: {
    host: "0.0.0.0",
    port: 4173,
    strictPort: true,
    allowedHosts: true,
    proxy: apiProxy,
  },
});
