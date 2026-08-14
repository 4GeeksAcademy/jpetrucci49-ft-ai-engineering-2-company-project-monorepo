"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { authFetch } from "@healthcore/auth";
import { parseApiError } from "@healthcore/auth";
import type { AuthMe, ProfileUpdatePayload } from "@healthcore/auth";

export function ProfileForm() {
  const [account, setAccount] = useState<AuthMe | null>(null);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const loadProfile = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await authFetch("/api/auth/me");
      if (!response.ok) {
        setError(await parseApiError(response));
        return;
      }

      const payload = (await response.json()) as AuthMe;
      setAccount(payload);
      setName(payload.profile.name);
      setPhone(payload.profile.phone ?? "");
      setAddress(payload.profile.address ?? "");
    } catch {
      setError("Unable to load profile.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProfile();
  }, [loadProfile]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setSubmitting(true);

    const payload: ProfileUpdatePayload = {};
    if (account && name !== account.profile.name) payload.name = name;
    if (account && phone !== (account.profile.phone ?? "")) payload.phone = phone || undefined;
    if (account && address !== (account.profile.address ?? "")) payload.address = address || undefined;

    if (Object.keys(payload).length === 0) {
      setMessage("No changes to save.");
      setSubmitting(false);
      return;
    }

    try {
      const response = await authFetch("/api/profiles/me", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        setError(await parseApiError(response));
        return;
      }

      setMessage("Profile updated.");
      await loadProfile();
    } catch {
      setError("Unable to save profile.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <p className="text-sm font-medium text-slate-600" role="status">
        Loading profile…
      </p>
    );
  }

  if (error && !account) {
    return (
      <p className="text-sm text-red-700" role="alert">
        {error}
      </p>
    );
  }

  return (
    <div className="max-w-lg rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h1 className="text-xl font-semibold text-slate-900">Account profile</h1>
      <p className="mt-1 text-sm text-slate-600">
        Update your contact details.{" "}
        <Link href="/account/change-password" className="font-medium text-teal-700 hover:underline">
          Change password
        </Link>
      </p>

      <dl className="mt-4 space-y-2 text-sm">
        <div>
          <dt className="font-medium text-slate-500">Email</dt>
          <dd className="text-slate-900">{account?.email}</dd>
        </div>
        <div>
          <dt className="font-medium text-slate-500">Role</dt>
          <dd className="text-slate-900">{account?.role}</dd>
        </div>
      </dl>

      <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
        <label className="block text-sm font-medium text-slate-700">
          Name
          <input
            type="text"
            name="name"
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </label>

        <label className="block text-sm font-medium text-slate-700">
          Phone
          <input
            type="tel"
            name="phone"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </label>

        <label className="block text-sm font-medium text-slate-700">
          Address
          <input
            type="text"
            name="address"
            value={address}
            onChange={(event) => setAddress(event.target.value)}
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

        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-60"
        >
          {submitting ? "Saving…" : "Save changes"}
        </button>
      </form>
    </div>
  );
}
