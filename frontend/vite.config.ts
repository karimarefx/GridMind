import { defineConfig } from "vitest/config";
export default defineConfig({
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
  build: {
    rollupOptions: { output: { manualChunks: { charts: ["recharts"] } } },
  },
  test: { include: ["tests/unit/**/*.test.ts"] },
});
