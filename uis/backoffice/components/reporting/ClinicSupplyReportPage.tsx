"use client";

import { FormEvent, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { useReloadableResource } from "@/components/inventory/useReloadableResource";
import {
  fetchLatestPipelineRun,
  fetchMonthlyClinicSupplyPerformance,
  type ClinicSupplyPerformance,
  type MonthlyClinicSupplyPerformance,
  type PipelineRunLatest,
} from "@/lib/api/reporting";
import { clinicLabel, countryLabel, formatMonthPeriod } from "@/lib/reporting/clinics";

const EMPTY_PACK: MonthlyClinicSupplyPerformance = { month_start: null, clinics: [] };

type ReportBundle = {
  pack: MonthlyClinicSupplyPerformance;
  latestRun: PipelineRunLatest | null;
};

const EMPTY_BUNDLE: ReportBundle = { pack: EMPTY_PACK, latestRun: null };

const EMPTY_CLINICS =
  "No clinic figures for this month. The pack is empty until the pipeline has run.";

function formatAmount(amount: number, currency: string): string {
  try {
    return new Intl.NumberFormat("en-GB", {
      style: "currency",
      currency,
      currencyDisplay: "code",
      minimumFractionDigits: 2,
    }).format(amount);
  } catch {
    return `${amount.toFixed(2)} ${currency}`;
  }
}

function sortClinics(clinics: ClinicSupplyPerformance[]): ClinicSupplyPerformance[] {
  return [...clinics].sort((left, right) =>
    clinicLabel(left.clinic_id).localeCompare(clinicLabel(right.clinic_id), "en")
  );
}

function MetricTable({
  title,
  empty,
  headers,
  rows,
}: {
  title: string;
  empty: string;
  headers: string[];
  rows: string[][];
}) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-base font-semibold text-slate-900">{title}</h2>
      {rows.length === 0 ? (
        <p className="mt-3 text-sm text-slate-600">{empty}</p>
      ) : (
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full text-left text-sm text-slate-800">
            <thead>
              <tr className="border-b border-slate-200 text-slate-600">
                {headers.map((header) => (
                  <th key={header} className="px-2 py-2 font-medium">
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((cells, index) => (
                <tr key={`${title}-${index}`} className="border-b border-slate-100 last:border-0">
                  {cells.map((cell, cellIndex) => (
                    <td key={`${title}-${index}-${cellIndex}`} className="px-2 py-2">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function formatRunWhen(run: PipelineRunLatest): string {
  const raw = run.finished_at ?? run.started_at;
  if (!raw) return "time unknown";
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return raw;
  return parsed.toLocaleString("en-GB", { timeZone: "UTC" }) + " UTC";
}

export function ClinicSupplyReportPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const monthStart = searchParams.get("month_start") ?? "";

  const load = useCallback(async () => {
    const [pack, latestRun] = await Promise.all([
      fetchMonthlyClinicSupplyPerformance(monthStart || undefined),
      fetchLatestPipelineRun(),
    ]);
    return { pack, latestRun };
  }, [monthStart]);

  const { data, error, isLoading, retry } = useReloadableResource<ReportBundle>(
    load,
    "Unable to load the clinic supply report.",
    EMPTY_BUNDLE
  );

  function applyMonth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const nextMonth = String(form.get("month_start") ?? "").trim();
    const next = new URLSearchParams();
    if (nextMonth) next.set("month_start", nextMonth);
    const query = next.toString();
    router.push(query ? `/reporting?${query}` : "/reporting");
  }

  const pack = data.pack;
  const clinics = sortClinics(pack.clinics);
  const period = formatMonthPeriod(pack.month_start);
  const empty = clinics.length === 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">
          Monthly Clinic Supply Performance Report
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          For Dr. Okonkwo and Claire — first working day of the month.
        </p>
      </div>

      <form
        key={monthStart}
        className="flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
        onSubmit={applyMonth}
      >
        <label className="text-sm text-slate-700">
          Month starting
          <input
            className="mt-1 block rounded-md border border-slate-300 px-2 py-1 text-slate-900"
            type="date"
            name="month_start"
            defaultValue={monthStart}
          />
        </label>
        <button
          type="submit"
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800"
        >
          Show month
        </button>
      </form>

      {pack.month_start ? (
        <p className="text-sm text-slate-700">
          <span className="font-medium">{period.heading}</span>
          {period.starting ? ` · ${period.starting}` : null}
        </p>
      ) : null}

      {data.latestRun ? (
        <p className="text-sm text-slate-600">
          Last computed {formatRunWhen(data.latestRun)} ({data.latestRun.status}).
        </p>
      ) : null}

      {isLoading ? <LoadingState label="Loading clinic supply report…" /> : null}
      {!isLoading && error ? <ErrorState message={error} onRetry={retry} homeHref="/" /> : null}

      {!isLoading && !error && empty ? (
        <p className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-600 shadow-sm">
          {EMPTY_CLINICS}
        </p>
      ) : null}

      {!isLoading && !error && !empty ? (
        <div className="grid gap-4">
          <MetricTable
            title="Supply Cost per Clinic"
            empty={EMPTY_CLINICS}
            headers={["Clinic", "Country", "Amount"]}
            rows={clinics.map((row) => [
              clinicLabel(row.clinic_id),
              countryLabel(row.country),
              formatAmount(row.total_supply_cost, row.currency),
            ])}
          />
          <MetricTable
            title="Supply Consumption Volume"
            empty={EMPTY_CLINICS}
            headers={["Clinic", "Country", "Consumption events"]}
            rows={clinics.map((row) => [
              clinicLabel(row.clinic_id),
              countryLabel(row.country),
              String(row.supply_consumption_count),
            ])}
          />
          <MetricTable
            title="Critical Stockout Frequency"
            empty={EMPTY_CLINICS}
            headers={["Clinic", "Country", "Stockout events"]}
            rows={clinics.map((row) => [
              clinicLabel(row.clinic_id),
              countryLabel(row.country),
              String(row.critical_stockout_count),
            ])}
          />
          <MetricTable
            title="Expiry Risk Count"
            empty={EMPTY_CLINICS}
            headers={["Clinic", "Country", "Batches flagged"]}
            rows={clinics.map((row) => [
              clinicLabel(row.clinic_id),
              countryLabel(row.country),
              String(row.expiry_risk_count),
            ])}
          />
        </div>
      ) : null}
    </div>
  );
}
