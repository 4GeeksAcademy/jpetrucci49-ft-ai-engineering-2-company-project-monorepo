import type { ReactNode } from "react";

type AlertVariant = "error" | "success" | "info";

const variantClasses: Record<AlertVariant, string> = {
  error: "border-red-200 bg-red-50 text-red-900",
  success: "border-emerald-200 bg-emerald-50 text-emerald-900",
  info: "border-sky-200 bg-sky-50 text-sky-900",
};

interface AlertProps {
  variant?: AlertVariant;
  children: ReactNode;
}

export function Alert({ variant = "info", children }: AlertProps) {
  return (
    <div className={`rounded-lg border px-4 py-3 text-sm ${variantClasses[variant]}`} role="alert">
      {children}
    </div>
  );
}
