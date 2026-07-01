"use client";

import { useState } from "react";
import { createRecord } from "@/lib/api/records";
import type { RecordFormValues } from "@/lib/validation";
import { CandidateForm } from "@/components/candidates/CandidateForm";
import { Button } from "@/components/ui/Button";

interface RegisterCandidatePanelProps {
  onCreated: () => void;
}

export function RegisterCandidatePanel({ onCreated }: RegisterCandidatePanelProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleSubmit = async (values: RecordFormValues) => {
    try {
      await createRecord(values);
      onCreated();
      setIsOpen(false);
      return true;
    } catch {
      return false;
    }
  };

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Register candidate</h2>
          <p className="text-sm text-slate-600">Add referrals or direct applications to the pipeline.</p>
        </div>
        <Button type="button" variant="secondary" onClick={() => setIsOpen((open) => !open)}>
          {isOpen ? "Close form" : "New candidate"}
        </Button>
      </div>

      {isOpen ? (
        <div className="mt-4 border-t border-slate-100 pt-4">
          <CandidateForm submitLabel="Register candidate" onSubmit={handleSubmit} />
        </div>
      ) : null}
    </section>
  );
}
