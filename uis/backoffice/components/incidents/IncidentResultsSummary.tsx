import type { AnalysisResult } from "@/types/incidents";
import { InvalidRecordsAlert } from "./InvalidRecordsAlert";

interface IncidentResultsSummaryProps {
  result: AnalysisResult;
}

function BreakdownTable({
  title,
  items,
  id,
}: {
  title: string;
  items: AnalysisResult["categories"];
  id: string;
}) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm" aria-labelledby={id}>
      <h3 id={id} className="text-lg font-semibold text-slate-900">
        {title}
      </h3>
      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-3 py-2">Code</th>
              <th className="px-3 py-2">Count</th>
              <th className="px-3 py-2">Share</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {items.map((item) => (
              <tr key={item.code}>
                <td className="px-3 py-2 font-medium">{item.code}</td>
                <td className="px-3 py-2 tabular-nums">{item.count}</td>
                <td className="px-3 py-2 tabular-nums">{item.percentage}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function IncidentResultsSummary({ result }: IncidentResultsSummaryProps) {
  return (
    <div className="space-y-6">
      <InvalidRecordsAlert
        invalidCount={result.totals.invalid_count}
        breakdown={result.invalid_breakdown}
      />

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm" aria-labelledby="totals-heading">
        <h3 id="totals-heading" className="text-lg font-semibold text-slate-900">
          General metrics
        </h3>
        <p className="mt-1 text-sm text-slate-500">
          Source: {result.source_filename} · Analyzed {new Date(result.analyzed_at).toLocaleString()}
        </p>
        <dl className="mt-4 grid gap-4 sm:grid-cols-3">
          <MetricCard label="Total records" value={String(result.totals.total)} />
          <MetricCard label="Valid records" value={String(result.totals.valid_count)} />
          <MetricCard label="Invalid / incomplete" value={String(result.totals.invalid_count)} />
        </dl>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <BreakdownTable title="Breakdown by category" items={result.categories} id="category-heading" />
        <BreakdownTable title="Breakdown by status" items={result.statuses} id="status-heading" />
      </div>

      {result.countries.length > 0 && (
        <BreakdownTable title="Breakdown by country" items={result.countries} id="country-heading" />
      )}

      <section
        className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
        aria-labelledby="satisfaction-heading"
      >
        <h3 id="satisfaction-heading" className="text-lg font-semibold text-slate-900">
          Satisfaction index (closed cases)
        </h3>
        <p className="mt-3 text-sm text-slate-700">
          Scored cases:{" "}
          <span className="font-medium tabular-nums">
            {result.satisfaction.scored_total} of {result.satisfaction.closed_total}
          </span>
          {" · "}
          Average score:{" "}
          <span className="font-medium tabular-nums">
            {result.satisfaction.average_score.toFixed(2)} / 5.00
          </span>
        </p>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">Score</th>
                <th className="px-3 py-2">Label</th>
                <th className="px-3 py-2">Count</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {result.satisfaction.scores.map((item) => (
                <tr key={item.score}>
                  <td className="px-3 py-2 font-medium tabular-nums">{item.score}</td>
                  <td className="px-3 py-2">{item.label}</td>
                  <td className="px-3 py-2 tabular-nums">{item.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 px-4 py-3">
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{value}</dd>
    </div>
  );
}
