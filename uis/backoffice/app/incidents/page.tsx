import { BackofficeShell } from "@/components/layout/BackofficeShell";
import { IncidentAnalysisPage } from "@/components/incidents/IncidentAnalysisPage";

export default function IncidentsPage() {
  return (
    <BackofficeShell>
      <IncidentAnalysisPage />
    </BackofficeShell>
  );
}
