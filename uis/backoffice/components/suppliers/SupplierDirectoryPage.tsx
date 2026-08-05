"use client";

import { useCallback, useEffect, useState } from "react";

import { SupplierFilters } from "@/components/suppliers/SupplierFilters";
import { SupplierRegistrationForm } from "@/components/suppliers/SupplierRegistrationForm";
import { SupplierTable } from "@/components/suppliers/SupplierTable";
import { fetchSuppliers, sortSuppliersByName } from "@/lib/api/suppliers";
import { SuppliersApiError, type Supplier, type SupplierListFilters } from "@/types/suppliers";

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof SuppliersApiError || error instanceof Error) {
    return error.message;
  }
  return fallback;
}

export function SupplierDirectoryPage() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [filters, setFilters] = useState<SupplierListFilters>({});
  const [listError, setListError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showRegistrationForm, setShowRegistrationForm] = useState(false);

  const reloadSuppliers = useCallback(async (activeFilters: SupplierListFilters) => {
    setIsLoading(true);
    setListError(null);

    try {
        const data = await fetchSuppliers(activeFilters);
      setSuppliers(sortSuppliersByName(data));
    } catch (error) {
      setSuppliers([]);
      setListError(getErrorMessage(error, "Unable to load suppliers."));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setListError(null);

      try {
        const data = await fetchSuppliers(filters);
        if (!cancelled) setSuppliers(sortSuppliersByName(data));
      } catch (error) {
        if (!cancelled) {
          setSuppliers([]);
          setListError(getErrorMessage(error, "Unable to load suppliers."));
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [filters]);

  function handleFiltersChange(next: SupplierListFilters) {
    setFilters(next);
  }

  function handleSupplierUpdated(updated: Supplier) {
    setSuppliers((current) =>
      sortSuppliersByName(current.map((item) => (item.id === updated.id ? updated : item)))
    );
  }

  function handleSupplierCreated(created: Supplier) {
    const matchesCountry = !filters.country || created.country === filters.country;
    const matchesCategory =
      !filters.category || created.categories.includes(filters.category);

    if (matchesCountry && matchesCategory) {
      setSuppliers((current) => sortSuppliersByName([...current, created]));
    } else {
      void reloadSuppliers(filters);
    }

    setShowRegistrationForm(false);
  }

  return (
    <div className="space-y-8">
      <section>
        <p className="text-xs font-medium uppercase tracking-wide text-teal-700">Operations</p>
        <h2 className="text-2xl font-semibold text-slate-900">Supplier Directory</h2>
        <p className="mt-2 max-w-3xl text-slate-600">
          Browse and manage HealthCore supplier contracts across USA and UK clinics — filter by market
          or category, register new vendors, and update rates or status in place.
        </p>
      </section>

      <section className="space-y-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <SupplierFilters filters={filters} disabled={isLoading} onChange={handleFiltersChange} />
          {!showRegistrationForm && (
            <button
              type="button"
              disabled={isLoading}
              onClick={() => setShowRegistrationForm(true)}
              className="inline-flex shrink-0 items-center justify-center rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Register new supplier
            </button>
          )}
        </div>

        {showRegistrationForm && (
          <SupplierRegistrationForm
            disabled={isLoading}
            onCreated={handleSupplierCreated}
            onCancel={() => setShowRegistrationForm(false)}
          />
        )}

        {isLoading && (
          <p className="text-sm font-medium text-teal-700" role="status" aria-live="polite">
            Loading suppliers…
          </p>
        )}

        {listError && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
            {listError}
          </div>
        )}

        {!isLoading && !listError && (
          <SupplierTable
            suppliers={suppliers}
            onSupplierUpdated={handleSupplierUpdated}
          />
        )}
      </section>
    </div>
  );
}
