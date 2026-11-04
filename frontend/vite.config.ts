import { defineConfig } from "vitest/config";
export default defineConfig({
  build: {
    rollupOptions: { output: { manualChunks: { charts: ["recharts"] } } },
  },
  test: { include: ["tests/unit/**/*.test.ts"] },
});
