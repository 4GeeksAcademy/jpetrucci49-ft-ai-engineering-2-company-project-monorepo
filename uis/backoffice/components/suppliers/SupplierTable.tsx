"use client";

import { useState, type FocusEvent } from "react";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import {
  deleteSupplier,
  formatRate,
  updateSupplierRate,
  updateSupplierStatus,
} from "@/lib/api/suppliers";
import {
  SUPPLIER_CATEGORY_LABELS,
  SuppliersApiError,
  type Supplier,
  type SupplierCategory,
  type SupplierStatus,
} from "@/types/suppliers";

interface SupplierTableProps {
  suppliers: Supplier[];
  disabled?: boolean;
  onSupplierUpdated: (supplier: Supplier) => void;
  onSupplierDeleted: (id: number) => void;
}

const buttonBase =
  "inline-flex items-center justify-center rounded-md border px-3 py-1.5 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50";

const numberInputClassName =
  "border-0 bg-transparent px-2 py-1 text-sm focus:outline-none [appearance:textfield] [-moz-appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none";

const rateCellWidthClassName = "w-44 min-w-[11rem] max-w-[11rem]";

function handleRateEditorBlur(
  event: FocusEvent<HTMLDivElement>,
  supplier: Supplier,
  onClose: (supplier: Supplier) => void
) {
  if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
    onClose(supplier);
  }
}

function EditIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden
      className={className}
    >
      <path d="m2.695 14.763-1.262 3.154a.5.5 0 0 0 .65.65l3.155-1.262a4 4 0 0 0 1.343-.885L17.5 5.501a2.121 2.121 0 0 0-3-3L3.58 13.42a4 4 0 0 0-.885 1.343Z" />
    </svg>
  );
}

function StatusBadge({ status }: { status: SupplierStatus }) {
  if (status === "active") {
    return (
      <span className="inline-flex rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-800">
        Active
      </span>
    );
  }

  return (
    <span className="inline-flex rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-900">
      Suspended
    </span>
  );
}

function formatCategories(categories: string[]): string {
  return categories
    .map((category) => SUPPLIER_CATEGORY_LABELS[category as SupplierCategory] ?? category)
    .join(", ");
}

function getRateDraft(supplier: Supplier, drafts: Record<number, string>): string {
  return drafts[supplier.id] ?? String(supplier.monthly_rate);
}

function isRateDirty(supplier: Supplier, drafts: Record<number, string>): boolean {
  const draft = getRateDraft(supplier, drafts);
  const parsed = Number(draft);
  return Number.isFinite(parsed) && parsed !== supplier.monthly_rate;
}

export function SupplierTable({
  suppliers,
  disabled,
  onSupplierUpdated,
  onSupplierDeleted,
}: SupplierTableProps) {
  const [rateDrafts, setRateDrafts] = useState<Record<number, string>>({});
  const [editingRateId, setEditingRateId] = useState<number | null>(null);
  const [rateErrors, setRateErrors] = useState<Record<number, string>>({});
  const [actionErrors, setActionErrors] = useState<Record<number, string>>({});
  const [busyRows, setBusyRows] = useState<Record<number, boolean>>({});
  const [supplierPendingRemoval, setSupplierPendingRemoval] = useState<Supplier | null>(null);
  const [isRemoving, setIsRemoving] = useState(false);

  function setRowBusy(id: number, busy: boolean) {
    setBusyRows((current) => ({ ...current, [id]: busy }));
  }

  function setRateError(id: number, message: string | null) {
    setRateErrors((current) => {
      if (!message) {
        const next = { ...current };
        delete next[id];
        return next;
      }
      return { ...current, [id]: message };
    });
  }

  function setActionError(id: number, message: string | null) {
    setActionErrors((current) => {
      if (!message) {
        const next = { ...current };
        delete next[id];
        return next;
      }
      return { ...current, [id]: message };
    });
  }

  function clearRateDraft(id: number) {
    setRateDrafts((current) => {
      const next = { ...current };
      delete next[id];
      return next;
    });
  }

  function startRateEdit(supplier: Supplier) {
    if (disabled || busyRows[supplier.id]) return;

    if (editingRateId !== null && editingRateId !== supplier.id) {
      clearRateDraft(editingRateId);
      setEditingRateId(null);
    }

    setRateError(supplier.id, null);
    setEditingRateId(supplier.id);
  }

  function cancelRateEdit(supplier: Supplier) {
    clearRateDraft(supplier.id);
    setEditingRateId(null);
  }

  async function commitRateEdit(supplier: Supplier): Promise<boolean> {
    if (!isRateDirty(supplier, rateDrafts)) {
      setEditingRateId(null);
      clearRateDraft(supplier.id);
      return true;
    }

    const draft = getRateDraft(supplier, rateDrafts);
    const monthlyRate = Number(draft);

    if (!Number.isFinite(monthlyRate) || monthlyRate <= 0) {
      setRateError(supplier.id, "Monthly rate must be greater than zero.");
      return false;
    }

    setRowBusy(supplier.id, true);
    setRateError(supplier.id, null);

    try {
      const updated = await updateSupplierRate(supplier.id, { monthly_rate: monthlyRate });
      onSupplierUpdated(updated);
      clearRateDraft(supplier.id);
      setEditingRateId(null);
      return true;
    } catch (error) {
      setRateError(
        supplier.id,
        error instanceof SuppliersApiError || error instanceof Error
          ? error.message
          : "Unable to update rate."
      );
      return false;
    } finally {
      setRowBusy(supplier.id, false);
    }
  }

  async function handleStatusToggle(supplier: Supplier) {
    const nextStatus: SupplierStatus = supplier.status === "active" ? "suspended" : "active";

    setRowBusy(supplier.id, true);
    setActionError(supplier.id, null);

    try {
      const updated = await updateSupplierStatus(supplier.id, { status: nextStatus });
      onSupplierUpdated(updated);
    } catch (error) {
      setActionError(
        supplier.id,
        error instanceof SuppliersApiError || error instanceof Error
          ? error.message
          : "Unable to update status."
      );
    } finally {
      setRowBusy(supplier.id, false);
    }
  }

  async function confirmDelete() {
    if (!supplierPendingRemoval) return;

    const supplier = supplierPendingRemoval;
    setIsRemoving(true);
    setRowBusy(supplier.id, true);
    setActionError(supplier.id, null);

    try {
      await deleteSupplier(supplier.id);
      setSupplierPendingRemoval(null);
      onSupplierDeleted(supplier.id);
    } catch (error) {
      setActionError(
        supplier.id,
        error instanceof SuppliersApiError || error instanceof Error
          ? error.message
          : "Unable to remove supplier."
      );
      setSupplierPendingRemoval(null);
    } finally {
      setIsRemoving(false);
      setRowBusy(supplier.id, false);
    }
  }

  if (suppliers.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-slate-300 bg-white px-4 py-8 text-center text-sm text-slate-600">
        No suppliers match the current filters.
      </p>
    );
  }

  return (
    <>
      <ConfirmDialog
        open={supplierPendingRemoval !== null}
        title="Remove supplier?"
        description={
          supplierPendingRemoval ? (
            <>
              Remove <span className="font-medium text-slate-900">{supplierPendingRemoval.name}</span> from
              the supplier directory? This cannot be undone.
            </>
          ) : null
        }
        confirmLabel={isRemoving ? "Removing…" : "Remove supplier"}
        cancelLabel="Keep supplier"
        confirmVariant="danger"
        busy={isRemoving}
        onConfirm={() => void confirmDelete()}
        onCancel={() => {
          if (!isRemoving) setSupplierPendingRemoval(null);
        }}
      />
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
          <tr>
            <th className="px-4 py-3">Name</th>
            <th className="px-4 py-3">Country</th>
            <th className="px-4 py-3">Categories</th>
            <th className={`px-4 py-3 ${rateCellWidthClassName}`}>Monthly rate</th>
            <th className="px-4 py-3">Compliance</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {suppliers.map((supplier) => {
            const isBusy = disabled || busyRows[supplier.id];
            const isSuspended = supplier.status === "suspended";

            return (
              <tr
                key={supplier.id}
                className={isSuspended ? "bg-slate-50/80 text-slate-600" : "text-slate-900"}
              >
                <td className="px-4 py-3 font-medium">{supplier.name}</td>
                <td className="px-4 py-3">{supplier.country}</td>
                <td className="px-4 py-3">{formatCategories(supplier.categories)}</td>
                <td className="px-4 py-3">
                  <div className={`flex flex-col gap-1 ${rateCellWidthClassName}`}>
                    {editingRateId === supplier.id ? (
                      <div
                        className="flex h-8 items-center gap-1"
                        onBlur={(event) => handleRateEditorBlur(event, supplier, cancelRateEdit)}
                      >
                        <div className="flex min-w-0 flex-1 overflow-hidden rounded-md border border-slate-400 bg-white shadow-sm ring-2 ring-inset ring-slate-200">
                          <input
                            type="number"
                            min={0.01}
                            step={0.01}
                            autoFocus
                            aria-label={`Monthly rate for ${supplier.name}`}
                            className={`min-w-0 flex-1 ${numberInputClassName}`}
                            value={getRateDraft(supplier, rateDrafts)}
                            disabled={isBusy}
                            onChange={(event) =>
                              setRateDrafts((current) => ({
                                ...current,
                                [supplier.id]: event.target.value,
                              }))
                            }
                            onKeyDown={(event) => {
                              if (event.key === "Enter") {
                                event.preventDefault();
                                void commitRateEdit(supplier);
                              }
                              if (event.key === "Escape") {
                                event.preventDefault();
                                cancelRateEdit(supplier);
                              }
                            }}
                          />
                          <span className="flex shrink-0 items-center border-l border-slate-300 bg-slate-50 px-2 text-xs font-medium text-slate-600">
                            {supplier.currency}
                          </span>
                        </div>
                        <button
                          type="button"
                          disabled={isBusy || !isRateDirty(supplier, rateDrafts)}
                          onClick={() => void commitRateEdit(supplier)}
                          className={`${buttonBase} shrink-0 px-2 py-1 border-slate-900 bg-slate-900 text-white hover:bg-slate-800`}
                        >
                          Save
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        disabled={isBusy}
                        onClick={() => startRateEdit(supplier)}
                        className="group flex h-8 w-full items-center justify-between gap-1.5 rounded-md border border-dashed border-slate-300 px-2 text-left tabular-nums transition-colors hover:border-slate-400 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                        aria-label={`Edit monthly rate for ${supplier.name}`}
                        title="Click to edit monthly rate"
                      >
                        <span className="truncate">{formatRate(supplier.monthly_rate, supplier.currency)}</span>
                        <EditIcon className="h-3.5 w-3.5 shrink-0 text-slate-400 group-hover:text-slate-600" />
                      </button>
                    )}
                    {rateErrors[supplier.id] && (
                      <p className="text-xs text-red-700" role="alert">
                        {rateErrors[supplier.id]}
                      </p>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">{supplier.compliance_agreement ?? "—"}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={supplier.status} />
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-col gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        disabled={isBusy}
                        onClick={() => handleStatusToggle(supplier)}
                        className={`${buttonBase} border-slate-300 bg-white hover:bg-slate-50`}
                      >
                        {supplier.status === "active" ? "Suspend" : "Activate"}
                      </button>
                      <button
                        type="button"
                        disabled={isBusy}
                        onClick={() => setSupplierPendingRemoval(supplier)}
                        className={`${buttonBase} border-red-200 bg-white text-red-700 hover:bg-red-50`}
                      >
                        Remove
                      </button>
                    </div>
                    {actionErrors[supplier.id] && (
                      <p className="text-xs text-red-700" role="alert">
                        {actionErrors[supplier.id]}
                      </p>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      </div>
    </>
  );
}
