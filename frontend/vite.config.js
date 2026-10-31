import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development, any request to /api/... is forwarded to the FastAPI backend.
// That means the frontend code can just call fetch("/api/...") with no CORS headaches.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": process.env.VITE_API_URL || "http://localhost:8000",
    },
  },
});
