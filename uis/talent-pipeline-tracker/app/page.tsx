import { CandidateListView } from "@/components/candidates/CandidateListView";
import { Spinner } from "@/components/ui/Spinner";
import { fetchRecords } from "@/lib/api/records";
import { Suspense } from "react";

interface HomePageProps {
  searchParams: Promise<{
    status?: string;
    stage?: string;
    search?: string;
  }>;
}

async function CandidateListLoader({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; stage?: string; search?: string }>;
}) {
  const params = await searchParams;
  const filters = {
    status: params.status ?? "",
    stage: params.stage ?? "",
    search: params.search ?? "",
  };

  let response = null;
  let error: string | null = null;

  try {
    response = await fetchRecords({
      status: filters.status || undefined,
      stage: filters.stage || undefined,
      search: filters.search || undefined,
      limit: 50,
    });
  } catch (fetchError) {
    error = fetchError instanceof Error ? fetchError.message : "Could not load candidates.";
  }

  return <CandidateListView response={response} error={error} filters={filters} />;
}

export default function HomePage({ searchParams }: HomePageProps) {
  return (
    <Suspense fallback={<Spinner label="Loading pipeline..." />}>
      <CandidateListLoader searchParams={searchParams} />
    </Suspense>
  );
}
