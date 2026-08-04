import type { InvalidBreakdownItem } from "@/types/incidents";

interface InvalidRecordsAlertProps {
  invalidCount: number;
  breakdown: InvalidBreakdownItem[];
}

export function InvalidRecordsAlert({ invalidCount, breakdown }: InvalidRecordsAlertProps) {
  if (invalidCount === 0) return null;

  const flagged = breakdown.filter((item) => item.count > 0);

  return (
    <section
      className="rounded-xl border border-amber-200 bg-amber-50 p-6"
      aria-labelledby="invalid-records-heading"
    >
      <h3 id="invalid-records-heading" className="text-lg font-semibold text-amber-900">
        Invalid or incomplete records detected
      </h3>
      <p className="mt-2 text-sm text-amber-800">
        {invalidCount} record{invalidCount === 1 ? "" : "s"} failed validation and were excluded from
        breakdown metrics. No patient identifiers are shown — rule counts only.
      </p>
      <ul className="mt-4 space-y-2 text-sm text-amber-900">
        {flagged.map((item) => (
          <li key={item.rule} className="flex justify-between gap-4 border-b border-amber-200/60 pb-2">
            <span>{item.label}</span>
            <span className="font-semibold tabular-nums">{item.count}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
