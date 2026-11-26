import type { Metadata } from "next";
import { Shield } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { navigationItem } from "@/lib/navigation";

const page = navigationItem("/cliff-guard");

export const metadata: Metadata = {
  title: page.label,
  description: page.description,
};

export default function CliffGuardPage() {
  return (
    <EmptyState
      icon={Shield}
      title="Cliff Guard is not available yet"
      description="When a verified, dated tariff configuration is loaded, this screen will show whether the household is near a higher slab. No threshold is displayed before that, and protected-consumer status is not assumed."
    />
  );
}
