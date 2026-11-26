import type { Metadata } from "next";
import { ActionPlanView } from "@/features/appliances/action-plan-view";
import { navigationItem } from "@/lib/navigation";

const page = navigationItem("/action-plan");

export const metadata: Metadata = {
  title: page.label,
  description: page.description,
};

export default function ActionPlanPage() {
  return <ActionPlanView />;
}
