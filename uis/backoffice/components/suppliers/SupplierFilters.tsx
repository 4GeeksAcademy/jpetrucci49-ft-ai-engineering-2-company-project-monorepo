"use client";

import {
  SUPPLIER_CATEGORIES,
  SUPPLIER_CATEGORY_LABELS,
  type SupplierCountry,
  type SupplierListFilters,
} from "@/types/suppliers";

interface SupplierFiltersProps {
  filters: SupplierListFilters;
  disabled?: boolean;
  onChange: (filters: SupplierListFilters) => void;
}

export function SupplierFilters({ filters, disabled, onChange }: SupplierFiltersProps) {
  return (
    <div className="flex flex-wrap items-end gap-4">
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">Country</span>
        <select
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900"
          value={filters.country ?? ""}
          disabled={disabled}
          onChange={(event) => {
            const value = event.target.value as SupplierCountry | "";
            onChange({
              ...filters,
              country: value === "" ? undefined : value,
            });
          }}
        >
          <option value="">All</option>
          <option value="USA">USA</option>
          <option value="UK">UK</option>
        </select>
      </label>

      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">Category</span>
        <select
          className="min-w-[220px] rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900"
          value={filters.category ?? ""}
          disabled={disabled}
          onChange={(event) => {
            const value = event.target.value;
            onChange({
              ...filters,
              category: value === "" ? undefined : value,
            });
          }}
        >
          <option value="">All</option>
          {SUPPLIER_CATEGORIES.map((category) => (
            <option key={category} value={category}>
              {SUPPLIER_CATEGORY_LABELS[category]}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
