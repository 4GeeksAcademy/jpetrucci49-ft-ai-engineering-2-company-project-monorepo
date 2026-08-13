"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { parseApiError } from "@healthcore/auth";
import { changePassword } from "@/lib/api/auth";

export function ChangePasswordForm() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);

    if (newPassword !== confirmPassword) {
      setError("New password and confirmation do not match.");
      return;
    }

    setSubmitting(true);

    try {
      const response = await changePassword(currentPassword, newPassword);
      if (!response.ok) {
        setError(await parseApiError(response));
        return;
      }

      setMessage("Password updated successfully.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch {
      setError("Unable to reach the server. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-lg rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h1 className="text-xl font-semibold text-slate-900">Change password</h1>
      <p className="mt-1 text-sm text-slate-600">Update your password while signed in.</p>

      <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
        <label className="block text-sm font-medium text-slate-700">
          Current password
          <input
            type="password"
            name="current_password"
            autoComplete="current-password"
            required
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </label>

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
          <p className="text-sm text-red-700" role="alert">
            {error}
          </p>
        ) : null}
        {message ? (
          <p className="text-sm text-teal-700" role="status">
            {message}
          </p>
        ) : null}

        <div className="flex flex-wrap items-center gap-4">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-60"
          >
            {submitting ? "Saving…" : "Update password"}
          </button>
          <Link href="/account/profile" className="text-sm font-medium text-teal-700 hover:underline">
            Back to profile
          </Link>
        </div>
      </form>
    </div>
  );
}
