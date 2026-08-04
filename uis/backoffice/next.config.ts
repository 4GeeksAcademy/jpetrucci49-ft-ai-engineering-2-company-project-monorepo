import type { NextConfig } from "next";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { withMonorepoAliases } from "../../packages/shared/next-config";

const appRoot = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  ...withMonorepoAliases(appRoot, {
    "@healthcore/utils": "src/utils/index.ts",
    "@healthcore/fixtures": "tests/utils/fixtures.ts",
    "@healthcore/utility-registry": "src/utility-registry.ts",
  }),
};

export default nextConfig;
