import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Local dev: custody-api:8001, profile-api:8002, instrument-api:8003, order-api:8004.
// In Docker, nginx routes by prefix.
const custodyTarget = process.env.VITE_CUSTODY_TARGET ?? "http://localhost:8001";
const profileTarget = process.env.VITE_PROFILE_TARGET ?? "http://localhost:8002";
const instrumentTarget = process.env.VITE_INSTRUMENT_TARGET ?? "http://localhost:8003";
const orderTarget = process.env.VITE_ORDER_TARGET ?? "http://localhost:8004";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api/custody": {
        target: custodyTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/api/instruments": {
        target: instrumentTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/api/universe": {
        target: instrumentTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/api/orders": {
        target: orderTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/api": {
        target: profileTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
