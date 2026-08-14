"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { parseApiError } from "@healthcore/auth";
import { FORGOT_PASSWORD_CONFIRMATION, forgotPassword } from "@/lib/api/auth";

export function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitted) return;

    setError(null);
    setSubmitting(true);

    try {
      const response = await forgotPassword(email);
      if (!response.ok) {
        setError(await parseApiError(response));
        return;
      }
      setSubmitted(true);
    } catch {
      setError("Unable to reach the server. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h1 className="text-xl font-semibold text-slate-900">Forgot password</h1>
      <p className="mt-1 text-sm text-slate-600">
        Enter your email and we&apos;ll send a reset link if the account exists.
      </p>

      {submitted ? (
        <p className="mt-6 text-sm text-teal-700" role="status">
          {FORGOT_PASSWORD_CONFIRMATION}
        </p>
      ) : (
        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <label className="block text-sm font-medium text-slate-700">
            Email
            <input
              type="email"
              name="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </label>

          {error ? (
            <p className="text-sm text-red-700" role="alert">
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-60"
          >
            {submitting ? "Sending…" : "Send reset link"}
          </button>
        </form>
      )}

      <p className="mt-4 text-center text-sm text-slate-600">
        <Link href="/login" className="font-medium text-teal-700 hover:underline">
          Back to sign in
        </Link>
      </p>
    </div>
  );
}
