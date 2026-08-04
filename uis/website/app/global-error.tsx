"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body className="min-h-full bg-slate-50 p-8 text-slate-900 antialiased">
        <h2 className="text-xl font-semibold">Something went wrong</h2>
        <p className="mt-2 text-sm text-slate-600">{error.message}</p>
        <button
          type="button"
          className="mt-4 rounded-md bg-slate-900 px-4 py-2 text-sm text-white"
          onClick={() => reset()}
        >
          Try again
        </button>
      </body>
    </html>
  );
}
