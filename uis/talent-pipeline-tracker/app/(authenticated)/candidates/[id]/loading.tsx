import { Spinner } from "@/components/ui/Spinner";

export default function CandidateDetailLoading() {
  return (
    <div className="py-12">
      <Spinner label="Loading candidate..." />
    </div>
  );
}
