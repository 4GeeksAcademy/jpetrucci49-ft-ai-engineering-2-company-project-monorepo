"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { parseApiError, parseApiFieldErrors } from "@healthcore/auth";
import { setToken } from "@healthcore/auth";
import type { TokenResponse, UserRegisterPayload } from "@healthcore/auth";

export function RegisterForm() {
  const router = useRouter();
  const [form, setForm] = useState<UserRegisterPayload>({
    email: "",
    password: "",
    name: "",
    phone: "",
    address: "",
  });
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function updateField<K extends keyof UserRegisterPayload>(key: K, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setFieldErrors({});
    setSubmitting(true);

    const payload: UserRegisterPayload = {
      email: form.email,
      password: form.password,
    };
    if (form.name?.trim()) payload.name = form.name.trim();
    if (form.phone?.trim()) payload.phone = form.phone.trim();
    if (form.address?.trim()) payload.address = form.address.trim();

    try {
      const registerResponse = await fetch("/api/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!registerResponse.ok) {
        setFieldErrors(await parseApiFieldErrors(registerResponse));
        setError(await parseApiError(registerResponse));
        return;
      }

      const loginResponse = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: form.email, password: form.password }),
      });

      if (!loginResponse.ok) {
        setError(await parseApiError(loginResponse));
        return;
      }

      const tokenPayload = (await loginResponse.json()) as TokenResponse;
      setToken(tokenPayload.access_token);
      router.replace("/");
    } catch {
      setError("Unable to reach the server. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h1 className="text-xl font-semibold text-slate-900">Create account</h1>
      <p className="mt-1 text-sm text-slate-600">Register for internal HealthCore tools.</p>

      <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
        <label className="block text-sm font-medium text-slate-700">
          Email
          <input
            type="email"
            name="email"
            autoComplete="email"
            required
            value={form.email}
            onChange={(event) => updateField("email", event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          {fieldErrors.email ? <span className="mt-1 block text-xs text-red-700">{fieldErrors.email}</span> : null}
        </label>

        <label className="block text-sm font-medium text-slate-700">
          Password
          <input
            type="password"
            name="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={form.password}
            onChange={(event) => updateField("password", event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          {fieldErrors.password ? (
            <span className="mt-1 block text-xs text-red-700">{fieldErrors.password}</span>
          ) : null}
        </label>

        <label className="block text-sm font-medium text-slate-700">
          Name
          <input
            type="text"
            name="name"
            autoComplete="name"
            value={form.name ?? ""}
            onChange={(event) => updateField("name", event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </label>

        <label className="block text-sm font-medium text-slate-700">
          Phone
          <input
            type="tel"
            name="phone"
            autoComplete="tel"
            value={form.phone ?? ""}
            onChange={(event) => updateField("phone", event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </label>

        <label className="block text-sm font-medium text-slate-700">
          Address
          <input
            type="text"
            name="address"
            autoComplete="street-address"
            value={form.address ?? ""}
            onChange={(event) => updateField("address", event.target.value)}
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
          {submitting ? "Creating account…" : "Register"}
        </button>
      </form>

      <p className="mt-4 text-center text-sm text-slate-600">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-teal-700 hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
