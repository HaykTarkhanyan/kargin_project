import { configDefaults, defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    // rules-tests need the Firestore emulator — they run via `npm run test:rules`.
    exclude: [...configDefaults.exclude, "rules-tests/**"],
  },
  resolve: { alias: { "@": fileURLToPath(new URL("./", import.meta.url)) } },
});
