import { defineConfig } from "vitest/config";

/** M2 utility tests only — auth/tracker suites use Jest (see npm run test:auth, test:tracker). */
export default defineConfig({
  test: {
    include: ["tests/utils/**/*.test.ts"],
    exclude: ["**/node_modules/**", "uis/**", "packages/**"],
  },
});
