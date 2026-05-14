import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Local dev: custody-api on 8001, profile-api on 8002.
// In Docker, nginx routes /api/custody/* → custodian-api and /api/* → profile-api.
const custodyTarget = process.env.VITE_CUSTODY_TARGET ?? "http://localhost:8001";
const profileTarget = process.env.VITE_PROFILE_TARGET ?? "http://localhost:8002";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // More specific prefix first — custody routes go to port 8001
      "/api/custody": {
        target: custodyTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      // Everything else (/api/admin, /api/profile, …) goes to port 8002
      "/api": {
        target: profileTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
