import Link from "next/link";
import { getStageLabel, getStatusLabel } from "@/lib/labels";
import { Badge } from "@/components/ui/Badge";
import type { RecordOut } from "@/types/record";

interface CandidateTableProps {
  candidates: RecordOut[];
}

export function CandidateTable({ candidates }: CandidateTableProps) {
  if (candidates.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center text-sm text-slate-600">
        No candidates match the current filters.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-4 py-3">Candidate</th>
            <th className="px-4 py-3">Position</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Stage</th>
            <th className="px-4 py-3">Notes</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {candidates.map((candidate) => (
            <tr key={candidate.id} className="hover:bg-slate-50">
              <td className="px-4 py-3">
                <Link href={`/candidates/${candidate.id}`} className="font-medium text-teal-800 hover:underline">
                  {candidate.full_name}
                </Link>
                <p className="text-xs text-slate-500">{candidate.email}</p>
              </td>
              <td className="px-4 py-3 text-slate-700">{candidate.position}</td>
              <td className="px-4 py-3">
                <Badge tone="status">{getStatusLabel(candidate.status)}</Badge>
              </td>
              <td className="px-4 py-3">
                <Badge tone="stage">{getStageLabel(candidate.stage)}</Badge>
              </td>
              <td className="px-4 py-3 text-slate-600">{candidate.notes_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
