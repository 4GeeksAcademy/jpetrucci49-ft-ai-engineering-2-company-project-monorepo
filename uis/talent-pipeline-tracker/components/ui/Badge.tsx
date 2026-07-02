import type { ReactNode } from "react";

interface BadgeProps {
  children: ReactNode;
  tone?: "neutral" | "status" | "stage";
}

const toneClasses = {
  neutral: "bg-slate-100 text-slate-700",
  status: "bg-teal-50 text-teal-800 ring-1 ring-teal-100",
  stage: "bg-indigo-50 text-indigo-800 ring-1 ring-indigo-100",
};

export function Badge({ children, tone = "neutral" }: BadgeProps) {
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${toneClasses[tone]}`}>
      {children}
    </span>
  );
}
