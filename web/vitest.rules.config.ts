import { defineConfig } from "vitest/config";

// Rules tests talk to the Firestore emulator — node environment, longer timeout,
// and deliberately excluded from the main jsdom config (vitest.config.ts).
export default defineConfig({
  test: { include: ["rules-tests/**/*.test.ts"], environment: "node", testTimeout: 20000 },
});
