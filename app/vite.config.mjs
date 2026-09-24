import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the page talks to the service through this proxy, which adds the
// shared token so the browser never needs to know it.
const SERVICE = `http://127.0.0.1:${process.env.LOCALAI_PORT || 4318}`;
const TOKEN = process.env.LOCALAI_TOKEN || "devtoken";
const withToken = {
  target: SERVICE,
  configure: (proxy) => proxy.on("proxyReq", (req) => req.setHeader("X-LocalAI-Token", TOKEN)),
};

export default defineConfig({
  plugins: [react()],
  build: { outDir: "dist" },
  server: {
    port: 5173,
    strictPort: true,
    proxy: { "/api": withToken, "/files": withToken, "/uploads": withToken },
  },
});
