import { Suspense } from "react";

import { ClinicSupplyReportPage } from "@/components/reporting/ClinicSupplyReportPage";
import { LoadingState } from "@/components/ui/LoadingState";

export default function ReportingPage() {
  return (
    <Suspense fallback={<LoadingState label="Loading clinic supply report…" />}>
      <ClinicSupplyReportPage />
    </Suspense>
  );
}
