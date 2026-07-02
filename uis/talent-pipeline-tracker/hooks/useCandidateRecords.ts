"use client";

import { useEffect, useRef, useState } from "react";
import { fetchRecords } from "@/lib/api/records";
import type { CandidateFilterValues } from "@/components/candidates/CandidateFilters";
import type { RecordsListResponse } from "@/types/record";

interface UseCandidateRecordsResult {
  response: RecordsListResponse | null;
  isPending: boolean;
  isRefetching: boolean;
  error: string | null;
  reload: () => void;
}

export function useCandidateRecords(
  filters: CandidateFilterValues,
  reloadToken = 0
): UseCandidateRecordsResult {
  const [response, setResponse] = useState<RecordsListResponse | null>(null);
  const [isPending, setIsPending] = useState(true);
  const [isRefetching, setIsRefetching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reloadCount, setReloadCount] = useState(0);
  const hasLoadedRef = useRef(false);

  useEffect(() => {
    let cancelled = false;

    if (hasLoadedRef.current) {
      setIsRefetching(true);
    }

    async function loadRecords() {
      try {
        const data = await fetchRecords({
          status: filters.status || undefined,
          stage: filters.stage || undefined,
          search: filters.search || undefined,
          limit: 50,
        });

        if (!cancelled) {
          setResponse(data);
          setError(null);
          hasLoadedRef.current = true;
          setIsPending(false);
          setIsRefetching(false);
        }
      } catch (fetchError) {
        if (!cancelled) {
          setError(fetchError instanceof Error ? fetchError.message : "Could not load candidates.");
          setIsPending(false);
          setIsRefetching(false);
        }
      }
    }

    void loadRecords();

    return () => {
      cancelled = true;
    };
  }, [filters.status, filters.stage, filters.search, reloadToken, reloadCount]);

  return {
    response,
    isPending,
    isRefetching,
    error,
    reload: () => setReloadCount((count) => count + 1),
  };
}
