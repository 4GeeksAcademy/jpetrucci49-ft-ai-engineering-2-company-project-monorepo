import Link from "next/link";

export function AppHeader() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">HealthCore Digital</p>
          <h1 className="text-lg font-semibold text-slate-900">People &amp; Talent — Pipeline Tracker</h1>
          <p className="text-sm text-slate-600">Executive Assistant search · Austin headquarters</p>
        </div>
        <Link
          href="/"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          All candidates
        </Link>
      </div>
    </header>
  );
}
