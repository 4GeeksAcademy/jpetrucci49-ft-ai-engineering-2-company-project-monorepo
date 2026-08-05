import { BackofficeShell } from "@/components/layout/BackofficeShell";
import { SupplierDirectoryPage } from "@/components/suppliers/SupplierDirectoryPage";

export default function SuppliersPage() {
  return (
    <BackofficeShell>
      <SupplierDirectoryPage />
    </BackofficeShell>
  );
}
