import { AuthGuard } from "@/components/auth/AuthGuard";
import { BackofficeShell } from "@/components/layout/BackofficeShell";

export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <BackofficeShell>{children}</BackofficeShell>
    </AuthGuard>
  );
}
