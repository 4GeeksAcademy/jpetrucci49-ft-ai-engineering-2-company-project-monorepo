/**
 * Single source of truth for cross-app navigation labels, paths, and URL helpers.
 * Import from `@healthcore/navigation` in all uis/* apps — do not duplicate labels locally.
 */

export const crossAppNav = {
  labels: {
    en: {
      publicSite: "Public site",
      utilities: "Utilities",
      talentPipeline: "Talent pipeline",
    },
    es: {
      publicSite: "Sitio público",
      utilities: "Utilidades",
      talentPipeline: "Pipeline de talento",
    },
  },
  paths: {
    backofficeUtilities: "/utilities",
  },
  appTitles: {
    backoffice: "Operations Backoffice",
    tracker: "People & Talent — Pipeline Tracker",
  },
} as const;

export type CrossAppNavLang = keyof typeof crossAppNav.labels;

export interface AppUrlEnv {
  website?: string;
  backoffice?: string;
  tracker?: string;
}

const defaultAppUrls = {
  website: "http://localhost:3000",
  backoffice: "http://localhost:3001",
  tracker: "http://localhost:3002",
} as const;

export function resolveAppUrls(env: AppUrlEnv = {}) {
  return {
    website: env.website?.replace(/\/$/, "") || defaultAppUrls.website,
    backoffice: env.backoffice?.replace(/\/$/, "") || defaultAppUrls.backoffice,
    tracker: env.tracker?.replace(/\/$/, "") || defaultAppUrls.tracker,
  };
}

export function backofficeUtilitiesUrl(backofficeBase: string): string {
  return `${backofficeBase.replace(/\/$/, "")}${crossAppNav.paths.backofficeUtilities}`;
}

/** English labels for internal tools (backoffice, tracker headers). */
export const crossAppNavLabelsEn = crossAppNav.labels.en;

/** Resolved cross-app URLs from standard Next.js public env vars. */
export const appUrls = resolveAppUrls({
  website: process.env.NEXT_PUBLIC_WEBSITE_URL,
  backoffice: process.env.NEXT_PUBLIC_BACKOFFICE_URL,
  tracker: process.env.NEXT_PUBLIC_TRACKER_URL,
});

/** Alias used by internal tool headers. */
export const crossAppNavLabels = crossAppNavLabelsEn;
