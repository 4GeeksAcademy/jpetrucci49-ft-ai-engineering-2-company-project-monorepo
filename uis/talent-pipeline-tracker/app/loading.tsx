import { Spinner } from "@/components/ui/Spinner";

export default function Loading() {
  return (
    <div className="py-12">
      <Spinner label="Loading pipeline..." />
    </div>
  );
}
