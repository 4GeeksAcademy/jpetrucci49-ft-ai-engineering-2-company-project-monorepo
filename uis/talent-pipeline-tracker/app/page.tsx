import { CandidateListView } from "@/components/candidates/CandidateListView";
import { Spinner } from "@/components/ui/Spinner";
import { Suspense } from "react";

export default function HomePage() {
  return (
    <Suspense fallback={<Spinner label="Loading pipeline..." />}>
      <CandidateListView />
    </Suspense>
  );
}
