import { CandidateDetailView } from "@/components/candidates/CandidateDetailView";
import { Alert } from "@/components/ui/Alert";
import { fetchNotes } from "@/lib/api/notes";
import { fetchRecord } from "@/lib/api/records";

interface CandidateDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function CandidateDetailPage({ params }: CandidateDetailPageProps) {
  const { id } = await params;

  let candidate = null;
  let notes = null;
  let error: string | null = null;

  try {
    const [record, notesResponse] = await Promise.all([fetchRecord(id), fetchNotes(id)]);
    candidate = record;
    notes = notesResponse.data;
  } catch (fetchError) {
    error = fetchError instanceof Error ? fetchError.message : "Could not load candidate.";
  }

  if (error || !candidate || !notes) {
    return <Alert variant="error">{error ?? "Could not load candidate."}</Alert>;
  }

  return <CandidateDetailView initialCandidate={candidate} initialNotes={notes} />;
}
