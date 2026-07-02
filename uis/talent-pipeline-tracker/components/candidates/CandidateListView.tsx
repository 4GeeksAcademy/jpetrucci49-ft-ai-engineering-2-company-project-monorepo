"use client";

import { useCallback, useEffect, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useFilterReset } from "@/components/layout/FilterResetProvider";
import { CandidateFilters, type CandidateFilterValues } from "@/components/candidates/CandidateFilters";
import { CandidateTable } from "@/components/candidates/CandidateTable";
import { RegisterCandidatePanel } from "@/components/candidates/RegisterCandidatePanel";
import { useCandidateRecords } from "@/hooks/useCandidateRecords";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";

function readFilters(searchParams: URLSearchParams): CandidateFilterValues {
  return {
    status: searchParams.get("status") ?? "",
    stage: searchParams.get("stage") ?? "",
    search: searchParams.get("search") ?? "",
  };
}

function filtersAreEmpty(filters: CandidateFilterValues): boolean {
  return !filters.status && !filters.stage && !filters.search;
}

export function CandidateListView() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { resetNonce, clearedFilters, releaseClearedFilters } = useFilterReset();

  const urlFilters = useMemo(() => readFilters(searchParams), [searchParams]);
  const filters = clearedFilters ?? urlFilters;

  const { response, isPending, isRefetching, error, reload } = useCandidateRecords(filters, resetNonce);

  const summaryText = response
    ? `${response.total} application${response.total === 1 ? "" : "s"} in the active Executive Assistant search.`
    : "Review applications for the Austin headquarters role.";

  useEffect(() => {
    if (clearedFilters && filtersAreEmpty(urlFilters)) {
      releaseClearedFilters();
    }
  }, [clearedFilters, releaseClearedFilters, urlFilters]);

  const updateFilters = useCallback(
    (next: Partial<CandidateFilterValues>) => {
      releaseClearedFilters();

      const params = new URLSearchParams(searchParams.toString());
      const merged = { ...filters, ...next };

      for (const [key, value] of Object.entries(merged)) {
        if (value) params.set(key, value);
        else params.delete(key);
      }

      const query = params.toString();
      router.replace(query ? `/?${query}` : "/", { scroll: false });
    },
    [filters, releaseClearedFilters, router, searchParams]
  );

  return (
    <div className="space-y-6">
      <section>
        <h2 className="text-2xl font-semibold text-slate-900">Candidate pipeline</h2>
        <p
          className="mt-1 flex items-center gap-2 text-sm text-slate-600"
          aria-live="polite"
          aria-busy={isRefetching}
        >
          <span className={isRefetching ? "opacity-70 transition-opacity" : undefined}>{summaryText}</span>
          {isRefetching ? (
            <span
              className="inline-block h-3.5 w-3.5 shrink-0 animate-spin rounded-full border-2 border-slate-300 border-t-teal-700"
              role="status"
              aria-label="Updating results"
            />
          ) : null}
        </p>
      </section>

      <CandidateFilters key={resetNonce} values={filters} onChange={updateFilters} />
      <RegisterCandidatePanel onCreated={reload} />

      {isPending ? <Spinner label="Loading candidates..." /> : null}
      {error ? <Alert variant="error">{error}</Alert> : null}
      {response ? (
        <div
          className={`transition-opacity duration-150 ${isRefetching ? "pointer-events-none opacity-60" : "opacity-100"}`}
        >
          <CandidateTable candidates={response.data} />
        </div>
      ) : null}
    </div>
  );
}
