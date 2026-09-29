"use client";

import { FormEvent, useEffect, useState } from "react";

import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import {
  getRfpSections,
  getRfpTicket,
  RfpApiError,
  type RfpSection,
  type RfpTicket,
  uploadRfpPdf,
} from "@/lib/api/rfp";

const POLL_MS = 3000;

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
  const [file, setFile] = useState<File | null>(null);
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
        if (next.status !== "analyzing") {
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

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Choose a PDF RFP to upload.");
      return;
    }
    setIsUploading(true);
    setError(null);
    setTicket(null);
    setSections([]);
    try {
      const created = await uploadRfpPdf(file);
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

  const summary = ticket?.handoff_json?.synthesizer_summary;

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-2xl font-semibold text-slate-900">RFP intake</h2>
        <p className="mt-2 max-w-2xl text-sm text-slate-600">
          For Tom Callahan (Revenue Cycle). Upload an institutional RFP PDF. Intake routes work to
          Revenue Cycle, Clinical Operations, and Compliance — without opening the original file.
        </p>
      </header>

      <form onSubmit={onSubmit} className="space-y-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <label htmlFor="rfp-pdf" className="block text-sm font-medium text-slate-800">
          RFP PDF
        </label>
        <input
          id="rfp-pdf"
          name="file"
          type="file"
          accept="application/pdf,.pdf"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          className="block w-full text-sm text-slate-700"
        />
        <button
          type="submit"
          disabled={isUploading}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          {isUploading ? "Uploading…" : "Upload and analyze"}
        </button>
      </form>

      {isUploading ? <LoadingState label="Creating ticket…" layout="inline" /> : null}
      {error ? (
        <ErrorState
          message={error}
          onRetry={() => {
            setError(null);
          }}
          homeHref="/"
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

          {summary ? <p className="text-sm text-slate-800">{summary}</p> : null}

          {sections.length > 0 && ticket.status === "intake_complete" ? (
            <div className="grid gap-3 md:grid-cols-3">
              {sections.map((section) => (
                <article key={section.department_id} className="rounded-md border border-slate-200 p-3">
                  <h3 className="text-sm font-semibold text-slate-900">{section.owner}</h3>
                  <p className="text-xs capitalize text-slate-500">{section.department_id}</p>
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
