import type { Metadata } from "next";
import { ListChecks } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { navigationItem } from "@/lib/navigation";

const page = navigationItem("/action-plan");

export const metadata: Metadata = {
  title: page.label,
  description: page.description,
};

export default function ActionPlanPage() {
  return (
    <EmptyState
      icon={ListChecks}
      title="A saved action plan is not available yet"
      description="The overview includes one sample action so the layout is clear. Actions are not stored, and savings are not calculated in this version."
    />
  );
}
