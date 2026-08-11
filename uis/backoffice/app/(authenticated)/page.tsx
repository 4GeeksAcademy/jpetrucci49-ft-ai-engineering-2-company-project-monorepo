import { OperationsDashboard } from "@/components/dashboard/OperationsDashboard";
import { getOperationsSnapshot } from "@/lib/operations";

export default function HomePage() {
  const data = getOperationsSnapshot();

  return <OperationsDashboard data={data} />;
}
