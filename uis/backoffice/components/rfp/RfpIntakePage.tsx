"use client";

import { useEffect, useRef, useState } from "react";

import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { RfpFilePicker } from "@/components/rfp/RfpFilePicker";
import {
  getRfpSections,
  getRfpTicket,
  RfpApiError,
  startRfpDraft,
  uploadRfpPdf,
  type RfpEvaluationResult,
  type RfpSection,
  type RfpTicket,
} from "@/lib/api/rfp";

const POLL_MS = 3000;

const DEPARTMENT_LABELS: Record<string, string> = {
  revenue: "Revenue Cycle",
  clinical: "Clinical Operations",
  compliance: "Compliance",
};

function departmentLabel(departmentId: string): string {
  return DEPARTMENT_LABELS[departmentId] ?? departmentId.replaceAll("_", " ");
}

function shouldPoll(ticket: RfpTicket): boolean {
  if (ticket.status === "analyzing") {
    return true;
  }
  if (ticket.error_code === "draft_pipeline_error") {
    return false;
  }
  return (
    (ticket.status === "drafting" || ticket.status === "under_evaluation") &&
    ticket.part2_handoff_json == null
  );
}

function canStartDraft(ticket: RfpTicket): boolean {
  if (ticket.status === "intake_complete") {
    return true;
  }
  return (
    ticket.error_code === "draft_pipeline_error" &&
    (ticket.status === "drafting" || ticket.status === "under_evaluation")
  );
}

function statusLabel(ticket: RfpTicket): string {
  if (ticket.status === "analyzing") {
    return "Analyzing";
  }
  if (ticket.status === "drafting") {
    return ticket.error_code === "draft_pipeline_error"
      ? "Draft failed — retry generate"
      : "Drafting";
  }
  if (ticket.status === "under_evaluation") {
    return "Under evaluation";
  }
  if (ticket.status === "needs_human_review") {
    return "Needs human review";
  }
  if (ticket.status === "intake_complete") {
    return ticket.phi_detected ? "Intake complete — PHI flagged for Compliance" : "Intake complete";
  }
  if (ticket.discard_reason === "pipeline_error") {
    return "Intake failed — re-upload";
  }
  return "Discarded (not an RFP)";
}

function checkLabel(pass: boolean | undefined): string {
  return pass ? "Pass" : "Fail";
}

function EvalSummary({ evaluation }: { evaluation: RfpEvaluationResult | null }) {
  if (!evaluation) {
    return null;
  }
  return (
    <div className="mt-3 space-y-1 text-xs text-slate-600">
      {evaluation.needs_human_review ? (
        <p className="font-semibold text-amber-800">Provisional — iteration limit</p>
      ) : (
        <p className="font-medium text-slate-700">
          {evaluation.overall_pass ? "Evaluation passed" : "Evaluation incomplete"}
        </p>
      )}
      <ul className="list-disc space-y-0.5 pl-4">
        <li>Readability: {checkLabel(evaluation.readability?.pass)}</li>
        <li>Relevance: {checkLabel(evaluation.relevance?.pass)}</li>
        <li>Compliance: {checkLabel(evaluation.compliance?.pass)}</li>
      </ul>
    </div>
  );
}

export function RfpIntakePage() {
  const chosenFile = useRef<File | null>(null);
  const [hasFile, setHasFile] = useState(false);
  const [ticket, setTicket] = useState<RfpTicket | null>(null);
  const [sections, setSections] = useState<RfpSection[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const ticketId = ticket?.ticket_id ?? null;
  const pollTicket = ticket != null && shouldPoll(ticket);

  useEffect(() => {
    if (!ticketId || !pollTicket) {
      return;
    }
    const activeTicketId = ticketId;
    let cancelled = false;

    async function refresh() {
      try {
        const next = await getRfpTicket(activeTicketId);
        if (cancelled) {
          return;
        }
        setTicket(next);
        const readyForSections =
          next.status === "intake_complete" ||
          next.part2_handoff_json != null ||
          next.status === "needs_human_review";
        if (readyForSections) {
          setSections(await getRfpSections(activeTicketId));
        }
      } catch (caught) {
        if (!cancelled) {
          setError(caught instanceof RfpApiError ? caught.message : "Unable to refresh ticket status.");
        }
      }
    }

    const timer = window.setInterval(() => {
      void refresh();
    }, POLL_MS);
    void refresh();
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [ticketId, pollTicket]);

  function onFileSelected(file: File) {
    chosenFile.current = file;
    setHasFile(true);
    setError(null);
  }

  async function onUpload() {
    const pdf = chosenFile.current;
    if (!pdf) {
      setError("Choose a PDF RFP to upload.");
      return;
    }
    setIsUploading(true);
    setError(null);
    setTicket(null);
    setSections([]);
    try {
      const created = await uploadRfpPdf(pdf);
      setTicket({
        ticket_id: created.ticket_id,
        rfp_id: null,
        status: created.status,
        discard_reason: null,
        error_code: null,
        phi_detected: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        metadata: null,
        handoff_json: null,
        part2_handoff_json: null,
      });
    } catch (caught) {
      setError(caught instanceof RfpApiError ? caught.message : "Unable to upload the RFP.");
    } finally {
      setIsUploading(false);
    }
  }

  async function onGenerateDraft() {
    if (!ticket) {
      return;
    }
    setIsGenerating(true);
    setError(null);
    try {
      const created = await startRfpDraft(ticket.ticket_id);
      setTicket({
        ...ticket,
        status: created.status,
        error_code: null,
        part2_handoff_json: null,
      });
    } catch (caught) {
      setError(caught instanceof RfpApiError ? caught.message : "Unable to start draft generation.");
    } finally {
      setIsGenerating(false);
    }
  }

  const showIntakeSections = sections.length > 0 && ticket != null && ticket.status !== "analyzing";

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-2xl font-semibold text-slate-900">RFP intake</h2>
        <p className="mt-2 max-w-2xl text-sm text-slate-600">
          Upload an institutional RFP as a PDF. Intake classifies the document and lists what Revenue
          Cycle, Clinical Operations, and Compliance each need to review — without showing the original
          file.
        </p>
      </header>

      <div className="space-y-3">
        <RfpFilePicker disabled={isUploading} onFileSelected={onFileSelected} />
        <button
          type="button"
          onClick={() => void onUpload()}
          disabled={isUploading || !hasFile}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          {isUploading ? "Uploading…" : "Upload and analyze"}
        </button>
      </div>

      {isUploading ? <LoadingState label="Creating ticket…" layout="inline" /> : null}
      {error ? (
        <ErrorState
          message={error}
          onRetry={() => {
            setError(null);
          }}
          retryLabel="Dismiss"
        />
      ) : null}

      {ticket ? (
        <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm" aria-live="polite">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Ticket</p>
            <p className="mt-1 font-mono text-sm text-slate-800">{ticket.ticket_id}</p>
            <p className="mt-2 text-sm font-semibold text-slate-900">{statusLabel(ticket)}</p>
            {ticket.status === "analyzing" ? (
              <LoadingState label="Conversion and department analysis running…" layout="inline" />
            ) : null}
            {shouldPoll(ticket) && ticket.status !== "analyzing" ? (
              <LoadingState label="Generating and evaluating proposal drafts…" layout="inline" />
            ) : null}
          </div>

          {ticket.metadata ? (
            <dl className="grid gap-2 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-slate-500">Client</dt>
                <dd className="text-slate-900">{ticket.metadata.client_name ?? "Not stated"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Country / currency</dt>
                <dd className="text-slate-900">
                  {ticket.metadata.client_country}
                  {ticket.metadata.currency ? ` · ${ticket.metadata.currency}` : ""}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Program</dt>
                <dd className="text-slate-900">{ticket.metadata.program_type.replaceAll("_", " ")}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Covered population</dt>
                <dd className="text-slate-900">{ticket.metadata.covered_population ?? "Open question"}</dd>
              </div>
            </dl>
          ) : null}

          {ticket.handoff_json?.synthesizer_summary ? (
            <p className="text-sm text-slate-800">{ticket.handoff_json.synthesizer_summary}</p>
          ) : null}

          {canStartDraft(ticket) ? (
            <button
              type="button"
              onClick={() => void onGenerateDraft()}
              disabled={isGenerating}
              className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
            >
              {isGenerating ? "Starting…" : "Generate proposal draft"}
            </button>
          ) : null}

          {showIntakeSections ? (
            <div className="grid gap-3 md:grid-cols-3">
              {sections.map((section) => (
                <article key={section.department_id} className="rounded-md border border-slate-200 p-3">
                  <h3 className="text-sm font-semibold text-slate-900">{departmentLabel(section.department_id)}</h3>
                  {section.owner ? (
                    <p className="text-xs text-slate-600">
                      Contact: <span className="font-medium text-slate-800">{section.owner}</span>
                    </p>
                  ) : (
                    <p className="text-xs text-slate-500">Department review</p>
                  )}
                  <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-slate-800">
                    {section.key_aspects.map((aspect) => (
                      <li key={aspect}>{aspect}</li>
                    ))}
                  </ul>
                  {section.open_questions.length > 0 ? (
                    <div className="mt-3">
                      <p className="text-xs font-medium uppercase text-slate-500">Ask them</p>
                      <ul className="mt-1 list-disc space-y-1 pl-4 text-sm text-slate-800">
                        {section.open_questions.map((question) => (
                          <li key={question}>{question}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {section.draft_content ? (
                    <div className="mt-3 border-t border-slate-100 pt-3">
                      <p className="text-xs font-medium uppercase text-slate-500">Draft</p>
                      <p className="mt-1 whitespace-pre-wrap text-sm text-slate-800">{section.draft_content}</p>
                      <EvalSummary evaluation={section.evaluation_results} />
                    </div>
                  ) : null}
                </article>
              ))}
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
