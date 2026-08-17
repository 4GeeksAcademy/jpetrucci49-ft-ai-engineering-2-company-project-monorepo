/** @type {import('jest').Config} */
export default {
  preset: "ts-jest/presets/default-esm",
  testEnvironment: "jsdom",
  roots: ["<rootDir>/packages/shared/auth"],
  testMatch: ["**/__tests__/**/*.test.ts"],
  extensionsToTreatAsEsm: [".ts"],
  moduleNameMapper: {
    "^(\\.{1,2}/.*)\\.js$": "$1",
  },
  transform: {
    "^.+\\.tsx?$": [
      "ts-jest",
      {
        useESM: true,
        tsconfig: {
          module: "ES2020",
          moduleResolution: "Bundler",
          target: "ES2020",
          strict: true,
        },
      },
    ],
  },
  collectCoverageFrom: [
    "packages/shared/auth/**/*.ts",
    "!packages/shared/auth/index.ts",
    "!packages/shared/auth/types.ts",
    "!packages/shared/auth/fetch.ts",
  ],
};
