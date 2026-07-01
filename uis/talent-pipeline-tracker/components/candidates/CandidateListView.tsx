"use client";

import { useRouter } from "next/navigation";
import { CandidateFilters, type CandidateFilterValues } from "@/components/candidates/CandidateFilters";
import { CandidateTable } from "@/components/candidates/CandidateTable";
import { RegisterCandidatePanel } from "@/components/candidates/RegisterCandidatePanel";
import { Alert } from "@/components/ui/Alert";
import type { RecordsListResponse } from "@/types/record";

interface CandidateListViewProps {
  response: RecordsListResponse | null;
  error: string | null;
  filters: CandidateFilterValues;
}

export function CandidateListView({ response, error, filters }: CandidateListViewProps) {
  const router = useRouter();

  const updateFilters = (next: Partial<CandidateFilterValues>) => {
    const params = new URLSearchParams();
    const merged = { ...filters, ...next };

    for (const [key, value] of Object.entries(merged)) {
      if (value) params.set(key, value);
    }

    const query = params.toString();
    router.replace(query ? `/?${query}` : "/", { scroll: false });
  };

  return (
    <div className="space-y-6">
      <section>
        <h2 className="text-2xl font-semibold text-slate-900">Candidate pipeline</h2>
        <p className="mt-1 text-sm text-slate-600">
          {response
            ? `${response.total} application${response.total === 1 ? "" : "s"} in the active Executive Assistant search.`
            : "Review applications for the Austin headquarters role."}
        </p>
      </section>

      <CandidateFilters
        key={`${filters.status}|${filters.stage}`}
        values={filters}
        onChange={updateFilters}
      />
      <RegisterCandidatePanel onCreated={() => router.refresh()} />

      {error ? <Alert variant="error">{error}</Alert> : null}
      {response ? <CandidateTable candidates={response.data} /> : null}
    </div>
  );
}
