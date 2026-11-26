import type { Metadata } from "next";
import { FileSearch } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { navigationItem } from "@/lib/navigation";

const page = navigationItem("/bill-auditor");

export const metadata: Metadata = {
  title: page.label,
  description: page.description,
};

export default function BillAuditorPage() {
  return (
    <EmptyState
      icon={FileSearch}
      title="Bill Auditor is not available yet"
      description="A later stage will compare a submitted bill with the household record and can flag a possible mismatch. This version does not read bills, and it does not judge them."
    />
  );
}
