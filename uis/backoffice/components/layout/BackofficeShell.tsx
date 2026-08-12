"use client";

import Link from "next/link";
import { LogoutButton } from "@/components/auth/LogoutButton";
import { buildAuthenticatedAppUrl } from "@healthcore/auth";
import { appUrls, crossAppNav, crossAppNavLabels } from "@healthcore/navigation";

const navItems = [
  { href: "/", label: "Dashboard" },
  { href: "/incidents", label: "Incidents" },
  { href: "/suppliers", label: "Suppliers" },
  { href: crossAppNav.paths.backofficeUtilities, label: crossAppNavLabels.utilities },
  { href: "/account/profile", label: "Account" },
] as const;

const crossAppLinks = [
  { href: appUrls.website, label: crossAppNavLabels.publicSite, authenticated: false },
  { href: appUrls.tracker, label: crossAppNavLabels.talentPipeline, authenticated: true },
] as const;

export function BackofficeShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-slate-900 text-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">HealthCore Digital</p>
            <h1 className="text-lg font-semibold">{crossAppNav.appTitles.backoffice}</h1>
          </div>
          <nav className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm" aria-label="Backoffice navigation">
            {navItems.map((item) => (
              <Link key={item.href} href={item.href} className="text-slate-200 hover:text-white hover:underline">
                {item.label}
              </Link>
            ))}
            <span className="hidden h-4 w-px bg-slate-600 sm:inline" aria-hidden="true" />
            {crossAppLinks.map((item) => (
              <a
                key={item.href}
                href={item.authenticated ? buildAuthenticatedAppUrl(item.href) : item.href}
                className="text-slate-400 hover:text-white hover:underline"
              >
                {item.label}
              </a>
            ))}
            <LogoutButton />
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
    </div>
  );
}
