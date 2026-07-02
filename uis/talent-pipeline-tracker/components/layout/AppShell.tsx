"use client";

import { AppHeader } from "@/components/layout/AppHeader";
import { FilterResetProvider } from "@/components/layout/FilterResetProvider";
import type { ReactNode } from "react";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <FilterResetProvider>
      <AppHeader />
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">{children}</main>
    </FilterResetProvider>
  );
}
