import path from "node:path";

type WebpackConfig = {
  resolve?: {
    alias?: Record<string, string | string[] | false | undefined>;
  };
};

/** Turbopack + webpack aliases for monorepo packages. */
export function withMonorepoAliases(
  appRoot: string,
  extraAliases: Record<string, string> = {},
) {
  const monorepoRoot = path.resolve(appRoot, "../..");
  const toMonorepo = (relativePath: string) => path.join(monorepoRoot, relativePath);

  const aliasTargets: Record<string, string> = {
    "@healthcore/navigation": toMonorepo("packages/shared/navigation/index.ts"),
    ...Object.fromEntries(
      Object.entries(extraAliases).map(([key, value]) => [
        key,
        path.isAbsolute(value) ? value : toMonorepo(value),
      ]),
    ),
  };

  const turbopackAliases = Object.fromEntries(
    Object.entries(aliasTargets).map(([key, target]) => [key, path.relative(appRoot, target)]),
  );

  return {
    turbopack: {
      root: monorepoRoot,
      resolveAlias: turbopackAliases,
    },
    webpack: (config: WebpackConfig) => {
      config.resolve ??= {};
      config.resolve.alias = {
        ...config.resolve.alias,
        ...aliasTargets,
      };
      return config;
    },
  };
}
