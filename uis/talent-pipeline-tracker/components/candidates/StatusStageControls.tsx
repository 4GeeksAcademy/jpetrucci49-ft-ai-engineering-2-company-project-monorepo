"use client";

import { useState } from "react";
import { patchRecord } from "@/lib/api/records";
import { statusOptions, stageOptions } from "@/lib/labels";
import { Alert } from "@/components/ui/Alert";
import { Field, SelectInput } from "@/components/ui/Field";
import type { RecordOut } from "@/types/record";

interface StatusStageControlsProps {
  candidate: RecordOut;
  onUpdated: (candidate: RecordOut) => void;
}

export function StatusStageControls({ candidate, onUpdated }: StatusStageControlsProps) {
  const [status, setStatus] = useState(candidate.status);
  const [stage, setStage] = useState(candidate.stage);
  const [isSaving, setIsSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const updateField = async (patch: { status?: string; stage?: string }) => {
    setIsSaving(true);
    setFeedback(null);
    try {
      const updated = await patchRecord(candidate.id, patch);
      onUpdated(updated);
      setStatus(updated.status);
      setStage(updated.stage);
      setFeedback({ type: "success", message: "Pipeline updated." });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not update candidate.";
      setFeedback({ type: "error", message });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div>
        <h2 className="text-base font-semibold text-slate-900">Pipeline controls</h2>
        <p className="text-sm text-slate-600">Update status or stage after calls and interviews.</p>
      </div>

      {feedback ? <Alert variant={feedback.type}>{feedback.message}</Alert> : null}

      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Status" htmlFor="detail-status">
          <SelectInput
            id="detail-status"
            value={status}
            disabled={isSaving}
            onChange={(event) => {
              const nextStatus = event.target.value;
              setStatus(nextStatus);
              void updateField({ status: nextStatus });
            }}
          >
            {statusOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </SelectInput>
        </Field>

        <Field label="Stage" htmlFor="detail-stage">
          <SelectInput
            id="detail-stage"
            value={stage}
            disabled={isSaving}
            onChange={(event) => {
              const nextStage = event.target.value;
              setStage(nextStage);
              void updateField({ stage: nextStage });
            }}
          >
            {stageOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </SelectInput>
        </Field>
      </div>
    </section>
  );
}
