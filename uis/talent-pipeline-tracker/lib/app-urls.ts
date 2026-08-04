/**
 * Re-exports shared navigation — env-specific app URLs resolved at runtime.
 */
import {
  backofficeUtilitiesUrl,
  crossAppNav,
  crossAppNavLabelsEn,
  resolveAppUrls,
} from "@healthcore/navigation";

export const appUrls = resolveAppUrls({
  website: process.env.NEXT_PUBLIC_WEBSITE_URL,
  backoffice: process.env.NEXT_PUBLIC_BACKOFFICE_URL,
  tracker: process.env.NEXT_PUBLIC_TRACKER_URL,
});

export { backofficeUtilitiesUrl, crossAppNav, crossAppNavLabelsEn as crossAppNavLabels };
