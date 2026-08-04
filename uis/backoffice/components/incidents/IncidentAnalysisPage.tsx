"use client";

import { useState } from "react";

import { IncidentFileUpload } from "@/components/incidents/IncidentFileUpload";
import { IncidentResultsSummary } from "@/components/incidents/IncidentResultsSummary";
import { analyzeIncidents, downloadBlob, exportIncidentResults } from "@/lib/api/incidents";
import type { AnalysisResult } from "@/types/incidents";
import { IncidentsApiError } from "@/types/incidents";

export function IncidentAnalysisPage() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  async function handleUpload(file: File) {
    setIsUploading(true);
    setUploadError(null);
    setDownloadError(null);

    try {
      const analysis = await analyzeIncidents(file);
      setResult(analysis);
    } catch (error) {
      setResult(null);
      if (error instanceof IncidentsApiError) {
        setUploadError(error.message);
      } else if (error instanceof Error) {
        setUploadError(error.message);
      } else {
        setUploadError("Unable to analyze the uploaded file.");
      }
    } finally {
      setIsUploading(false);
    }
  }

  async function handleLoadSample() {
    setIsUploading(true);
    setUploadError(null);
    setDownloadError(null);

    try {
      const response = await fetch("/samples/incidents.csv");
      if (!response.ok) {
        throw new Error("Sample file is not available.");
      }
      const blob = await response.blob();
      const file = new File([blob], "incidents.csv", { type: "text/csv" });
      const analysis = await analyzeIncidents(file);
      setResult(analysis);
    } catch (error) {
      setResult(null);
      if (error instanceof IncidentsApiError) {
        setUploadError(error.message);
      } else if (error instanceof Error) {
        setUploadError(error.message);
      } else {
        setUploadError("Unable to load the sample file.");
      }
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDownload() {
    if (!result) {
      setDownloadError("Upload and analyze a CSV file before downloading results.");
      return;
    }

    setIsDownloading(true);
    setDownloadError(null);

    try {
      const blob = await exportIncidentResults();
      downloadBlob(blob, "results.csv");
    } catch (error) {
      if (error instanceof IncidentsApiError) {
        setDownloadError(error.message);
      } else if (error instanceof Error) {
        setDownloadError(error.message);
      } else {
        setDownloadError("Unable to download results.");
      }
    } finally {
      setIsDownloading(false);
    }
  }

  return (
    <div className="space-y-8">
      <section>
        <p className="text-xs font-medium uppercase tracking-wide text-teal-700">Patient Experience</p>
        <h2 className="text-2xl font-semibold text-slate-900">Patient Incident Analysis</h2>
        <p className="mt-2 max-w-3xl text-slate-600">
          Upload a monthly incident export from Patient Experience coordinators. The tool validates each
          record, summarizes category and status trends, and reports satisfaction scores for closed cases —
          without exposing patient identifiers.
        </p>
      </section>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
        <div className="min-w-0 flex-1">
          <IncidentFileUpload onFileSelected={handleUpload} disabled={isUploading} />
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 sm:w-64">
          <p className="text-sm font-medium text-slate-900">Try the sample file</p>
          <p className="mt-1 text-xs text-slate-500">
            In remote dev, the file picker opens your local computer — not this workspace. Use the sample
            button or drag the file from the editor file tree.
          </p>
          <button
            type="button"
            onClick={handleLoadSample}
            disabled={isUploading}
            className="mt-3 w-full rounded-lg border border-teal-600 px-3 py-2 text-sm font-medium text-teal-700 hover:bg-teal-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Load sample incidents.csv
          </button>
        </div>
      </div>

      {isUploading && (
        <p className="text-sm font-medium text-teal-700" role="status" aria-live="polite">
          Analyzing uploaded file…
        </p>
      )}

      {uploadError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
          {uploadError}
        </div>
      )}

      {!result && !isUploading && !uploadError && (
        <p className="text-sm text-slate-500">
          No analysis yet. Upload a CSV export to see totals, breakdowns, and satisfaction metrics.
        </p>
      )}

      {result && (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={handleDownload}
              disabled={isDownloading}
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isDownloading ? "Preparing download…" : "Download results CSV"}
            </button>
          </div>

          {downloadError && (
            <div
              className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
              role="alert"
            >
              {downloadError}
            </div>
          )}

          <IncidentResultsSummary result={result} />
        </>
      )}
    </div>
  );
}
