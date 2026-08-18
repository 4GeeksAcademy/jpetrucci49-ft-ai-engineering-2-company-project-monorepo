export default {
  preset: "ts-jest/presets/default-esm",
  testEnvironment: "node",
  roots: ["<rootDir>/__tests__"],
  testMatch: ["**/*.test.ts"],
  extensionsToTreatAsEsm: [".ts"],
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/$1",
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
          paths: {
            "@/*": ["./*"],
          },
        },
      },
    ],
  },
  collectCoverageFrom: ["lib/**/*.ts", "!lib/api/**"],
};
