import { Suspense } from "react";

import { SupplierDirectoryPage } from "@/components/suppliers/SupplierDirectoryPage";

export default function SuppliersPage() {
  return (
    <Suspense
      fallback={
        <p className="text-sm font-medium text-teal-700" role="status" aria-live="polite">
          Loading suppliers…
        </p>
      }
    >
      <SupplierDirectoryPage />
    </Suspense>
  );
}
