"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useState } from "react";

import { parseApiError } from "@healthcore/auth";
import { RESET_PASSWORD_LOGIN_MESSAGE, resetPassword } from "@/lib/api/auth";

export function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!token) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-xl font-semibold text-slate-900">Reset password</h1>
        <p className="mt-4 text-sm text-red-700" role="alert">
          This reset link is invalid or incomplete.
        </p>
        <p className="mt-4 text-center text-sm text-slate-600">
          <Link href="/forgot-password" className="font-medium text-teal-700 hover:underline">
            Request a new reset link
          </Link>
        </p>
      </div>
    );
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;

    setError(null);

    if (newPassword !== confirmPassword) {
      setError("New password and confirmation do not match.");
      return;
    }

    setSubmitting(true);

    try {
      const response = await resetPassword(token, newPassword);
      if (!response.ok) {
        setError(await parseApiError(response));
        return;
      }

      const params = new URLSearchParams({ message: RESET_PASSWORD_LOGIN_MESSAGE });
      router.replace(`/login?${params.toString()}`);
    } catch {
      setError("Unable to reach the server. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h1 className="text-xl font-semibold text-slate-900">Reset password</h1>
      <p className="mt-1 text-sm text-slate-600">Choose a new password for your account.</p>

      <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
        <label className="block text-sm font-medium text-slate-700">
          New password
          <input
            type="password"
            name="new_password"
            autoComplete="new-password"
            required
            minLength={8}
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </label>

        <label className="block text-sm font-medium text-slate-700">
          Confirm new password
          <input
            type="password"
            name="confirm_password"
            autoComplete="new-password"
            required
            minLength={8}
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </label>

        {error ? (
          <div className="space-y-2">
            <p className="text-sm text-red-700" role="alert">
              {error}
            </p>
            <p className="text-sm text-slate-600">
              <Link href="/forgot-password" className="font-medium text-teal-700 hover:underline">
                Request a new reset link
              </Link>
            </p>
          </div>
        ) : null}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-60"
        >
          {submitting ? "Saving…" : "Reset password"}
        </button>
      </form>
    </div>
  );
}
