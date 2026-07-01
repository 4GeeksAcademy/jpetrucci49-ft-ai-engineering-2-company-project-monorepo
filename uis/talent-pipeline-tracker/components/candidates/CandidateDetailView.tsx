"use client";

import { useState } from "react";
import Link from "next/link";
import { replaceRecord } from "@/lib/api/records";
import { getStageLabel, getStatusLabel } from "@/lib/labels";
import type { RecordFormValues } from "@/lib/validation";
import { CandidateForm } from "@/components/candidates/CandidateForm";
import { NotesSection } from "@/components/candidates/NotesSection";
import { StatusStageControls } from "@/components/candidates/StatusStageControls";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import type { NoteOut } from "@/types/note";
import type { RecordOut } from "@/types/record";

interface CandidateDetailViewProps {
  initialCandidate: RecordOut;
  initialNotes: NoteOut[];
}

function DetailField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 text-sm text-slate-900">{value}</dd>
    </div>
  );
}

export function CandidateDetailView({ initialCandidate, initialNotes }: CandidateDetailViewProps) {
  const [candidate, setCandidate] = useState(initialCandidate);
  const [isEditing, setIsEditing] = useState(false);

  const handleReplace = async (values: RecordFormValues) => {
    try {
      const updated = await replaceRecord(candidate.id, values);
      setCandidate(updated);
      setIsEditing(false);
      return true;
    } catch {
      return false;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link href="/" className="text-sm font-medium text-teal-700 hover:underline">
            ← Back to pipeline
          </Link>
          <h2 className="mt-2 text-2xl font-semibold text-slate-900">{candidate.full_name}</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            <Badge tone="status">{getStatusLabel(candidate.status)}</Badge>
            <Badge tone="stage">{getStageLabel(candidate.stage)}</Badge>
          </div>
        </div>
        <Button type="button" variant="secondary" onClick={() => setIsEditing((open) => !open)}>
          {isEditing ? "Close editor" : "Edit candidate"}
        </Button>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <DetailField label="Email" value={candidate.email} />
          <DetailField label="Phone" value={candidate.phone} />
          <DetailField label="Position" value={candidate.position} />
          <DetailField label="Years of experience" value={String(candidate.experience_years)} />
          <DetailField label="Application date" value={new Date(candidate.applied_at).toLocaleString()} />
          <DetailField label="Last updated" value={new Date(candidate.updated_at).toLocaleString()} />
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">LinkedIn</dt>
            <dd className="mt-1 text-sm">
              {candidate.linkedin_url ? (
                <a href={candidate.linkedin_url} className="text-teal-700 hover:underline" target="_blank" rel="noreferrer">
                  View profile
                </a>
              ) : (
                <span className="text-slate-500">Not provided</span>
              )}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">CV</dt>
            <dd className="mt-1 text-sm">
              {candidate.cv_url ? (
                <a href={candidate.cv_url} className="text-teal-700 hover:underline" target="_blank" rel="noreferrer">
                  View CV
                </a>
              ) : (
                <span className="text-slate-500">Not provided</span>
              )}
            </dd>
          </div>
        </dl>
      </section>

      <StatusStageControls candidate={candidate} onUpdated={setCandidate} />

      {isEditing ? (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="mb-4 text-base font-semibold text-slate-900">Edit candidate data</h3>
          <CandidateForm
            initialValues={candidate}
            submitLabel="Save changes"
            onSubmit={handleReplace}
            onCancel={() => setIsEditing(false)}
          />
        </section>
      ) : null}

      <NotesSection recordId={candidate.id} initialNotes={initialNotes} />
    </div>
  );
}
