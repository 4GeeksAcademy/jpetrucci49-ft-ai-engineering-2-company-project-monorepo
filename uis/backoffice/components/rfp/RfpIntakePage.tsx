"use client";

import { useEffect, useRef, useState } from "react";

import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { RfpFilePicker } from "@/components/rfp/RfpFilePicker";
import {
  getRfpSections,
  getRfpTicket,
  RfpApiError,
  type RfpSection,
  type RfpTicket,
  uploadRfpPdf,
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

function statusLabel(ticket: RfpTicket): string {
  if (ticket.status === "analyzing") {
    return "Analyzing";
  }
  if (ticket.status === "intake_complete") {
    return ticket.phi_detected ? "Intake complete — PHI flagged for Compliance" : "Intake complete";
  }
  if (ticket.discard_reason === "pipeline_error") {
    return "Intake failed — re-upload";
  }
  return "Discarded (not an RFP)";
}

export function RfpIntakePage() {
  const chosenFile = useRef<File | null>(null);
  const [hasFile, setHasFile] = useState(false);
  const [ticket, setTicket] = useState<RfpTicket | null>(null);
  const [sections, setSections] = useState<RfpSection[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const ticketId = ticket?.ticket_id ?? null;
  const ticketStatus = ticket?.status ?? null;

  useEffect(() => {
    if (!ticketId || ticketStatus !== "analyzing") {
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
        if (next.status === "intake_complete") {
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
  }, [ticketId, ticketStatus]);

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
      });
    } catch (caught) {
      setError(caught instanceof RfpApiError ? caught.message : "Unable to upload the RFP.");
    } finally {
      setIsUploading(false);
    }
  }

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
          retryLabel="Try another upload"
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

          {ticket.status === "intake_complete" && ticket.handoff_json?.synthesizer_summary ? (
            <p className="text-sm text-slate-800">{ticket.handoff_json.synthesizer_summary}</p>
          ) : null}

          {sections.length > 0 && ticket.status === "intake_complete" ? (
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
                </article>
              ))}
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
