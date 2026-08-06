"use client";

import { useEffect, useRef, useState } from "react";

import { createSupplier } from "@/lib/api/suppliers";
import {
  COUNTRY_CURRENCY,
  SUPPLIER_CATEGORIES,
  SUPPLIER_CATEGORY_LABELS,
  SuppliersApiError,
  type Supplier,
  type SupplierCountry,
  type SupplierCreatePayload,
  type SupplierStatus,
} from "@/types/suppliers";

interface SupplierRegistrationFormProps {
  disabled?: boolean;
  onCreated: (supplier: Supplier) => void;
  onCancel: () => void;
}

const emptyForm: SupplierCreatePayload = {
  name: "",
  country: "USA",
  categories: [],
  monthly_rate: 0,
  currency: "USD",
  status: "active",
  compliance_agreement: null,
  contract_renewal_date: null,
  contact_email: null,
  notes: null,
};

export function SupplierRegistrationForm({ disabled, onCreated, onCancel }: SupplierRegistrationFormProps) {
  const [form, setForm] = useState<SupplierCreatePayload>(emptyForm);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const nameInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    nameInputRef.current?.focus();
  }, []);

  function updateCountry(country: SupplierCountry) {
    setForm((current) => ({
      ...current,
      country,
      currency: COUNTRY_CURRENCY[country],
    }));
  }

  function toggleCategory(category: string) {
    setForm((current) => {
      const selected = current.categories.includes(category)
        ? current.categories.filter((item) => item !== category)
        : [...current.categories, category];
      return { ...current, categories: selected };
    });
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const supplier = await createSupplier(form);
      onCreated(supplier);
      setForm({ ...emptyForm, country: form.country, currency: COUNTRY_CURRENCY[form.country] });
    } catch (err) {
      setError(
        err instanceof SuppliersApiError || err instanceof Error
          ? err.message
          : "Unable to register supplier."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
    >
      <h3 className="text-lg font-semibold text-slate-900">Register new supplier</h3>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm sm:col-span-2">
          <span className="font-medium text-slate-700">Name *</span>
          <input
            ref={nameInputRef}
            required
            type="text"
            className="rounded-md border border-slate-300 px-3 py-2"
            value={form.name}
            disabled={disabled || isSubmitting}
            onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Country *</span>
          <select
            className="rounded-md border border-slate-300 px-3 py-2"
            value={form.country}
            disabled={disabled || isSubmitting}
            onChange={(event) => updateCountry(event.target.value as SupplierCountry)}
          >
            <option value="USA">USA</option>
            <option value="UK">UK</option>
          </select>
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Currency *</span>
          <input
            type="text"
            readOnly
            className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-slate-600"
            value={form.currency}
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Monthly rate *</span>
          <input
            required
            type="number"
            min={0.01}
            step={0.01}
            className="rounded-md border border-slate-300 px-3 py-2"
            value={form.monthly_rate || ""}
            disabled={disabled || isSubmitting}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                monthly_rate: Number(event.target.value),
              }))
            }
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Status *</span>
          <select
            className="rounded-md border border-slate-300 px-3 py-2"
            value={form.status}
            disabled={disabled || isSubmitting}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                status: event.target.value as SupplierStatus,
              }))
            }
          >
            <option value="active">Active</option>
            <option value="suspended">Suspended</option>
          </select>
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Compliance agreement</span>
          <select
            className="rounded-md border border-slate-300 px-3 py-2"
            value={form.compliance_agreement ?? ""}
            disabled={disabled || isSubmitting}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                compliance_agreement: event.target.value === "" ? null : (event.target.value as "BAA" | "DPA" | "both"),
              }))
            }
          >
            <option value="">Not applicable</option>
            <option value="BAA">BAA</option>
            <option value="DPA">DPA</option>
            <option value="both">Both</option>
          </select>
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Contract renewal date</span>
          <input
            type="date"
            className="rounded-md border border-slate-300 px-3 py-2"
            value={form.contract_renewal_date ?? ""}
            disabled={disabled || isSubmitting}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                contract_renewal_date: event.target.value || null,
              }))
            }
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Contact email</span>
          <input
            type="email"
            className="rounded-md border border-slate-300 px-3 py-2"
            value={form.contact_email ?? ""}
            disabled={disabled || isSubmitting}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                contact_email: event.target.value || null,
              }))
            }
          />
        </label>

        <label className="flex flex-col gap-1 text-sm sm:col-span-2">
          <span className="font-medium text-slate-700">Notes</span>
          <textarea
            rows={2}
            className="rounded-md border border-slate-300 px-3 py-2"
            value={form.notes ?? ""}
            disabled={disabled || isSubmitting}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                notes: event.target.value || null,
              }))
            }
          />
        </label>
      </div>

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium text-slate-700">Categories *</legend>
        <div className="flex flex-wrap gap-2">
          {SUPPLIER_CATEGORIES.map((category) => (
            <label
              key={category}
              className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-2 py-1 text-sm"
            >
              <input
                type="checkbox"
                checked={form.categories.includes(category)}
                disabled={disabled || isSubmitting}
                onChange={() => toggleCategory(category)}
              />
              {SUPPLIER_CATEGORY_LABELS[category]}
            </label>
          ))}
        </div>
      </fieldset>

      {error && (
        <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
          {error}
        </p>
      )}

      <div className="flex flex-wrap gap-3">
        <button
          type="submit"
          disabled={disabled || isSubmitting || form.categories.length === 0}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting ? "Registering…" : "Register supplier"}
        </button>
        <button
          type="button"
          disabled={isSubmitting}
          onClick={onCancel}
          className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
