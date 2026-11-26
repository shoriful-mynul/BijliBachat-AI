import type { Metadata } from "next";
import { Gauge } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { navigationItem } from "@/lib/navigation";

const page = navigationItem("/meter-readings");

export const metadata: Metadata = {
  title: page.label,
  description: page.description,
};

export default function MeterReadingsPage() {
  return (
    <EmptyState
      icon={Gauge}
      title="Meter readings are not available yet"
      description="Checkpoints will be entered by hand, or confirmed from a photo. They are not a live feed from the meter. The overview shows one sample checkpoint only."
    />
  );
}
