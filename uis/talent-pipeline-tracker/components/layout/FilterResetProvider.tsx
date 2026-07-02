"use client";

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import type { CandidateFilterValues } from "@/components/candidates/CandidateFilters";

interface FilterResetContextValue {
  resetNonce: number;
  clearedFilters: CandidateFilterValues | null;
  clearAllFilters: () => void;
  releaseClearedFilters: () => void;
}

const emptyFilters: CandidateFilterValues = {
  status: "",
  stage: "",
  search: "",
};

const FilterResetContext = createContext<FilterResetContextValue | null>(null);

export function FilterResetProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [resetNonce, setResetNonce] = useState(0);
  const [clearedFilters, setClearedFilters] = useState<CandidateFilterValues | null>(null);

  const clearAllFilters = useCallback(() => {
    setClearedFilters(emptyFilters);
    setResetNonce((current) => current + 1);

    if (pathname === "/") {
      window.history.replaceState(window.history.state, "", "/");
      return;
    }

    router.push("/");
  }, [pathname, router]);

  const releaseClearedFilters = useCallback(() => {
    setClearedFilters(null);
  }, []);

  return (
    <FilterResetContext.Provider
      value={{ resetNonce, clearedFilters, clearAllFilters, releaseClearedFilters }}
    >
      {children}
    </FilterResetContext.Provider>
  );
}

export function useFilterReset(): FilterResetContextValue {
  const context = useContext(FilterResetContext);
  if (!context) {
    throw new Error("useFilterReset must be used within FilterResetProvider.");
  }
  return context;
}
