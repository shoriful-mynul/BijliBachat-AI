import type { Metadata } from "next";
import { Settings } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { AppearanceForm } from "@/features/settings/appearance-form";
import { SampleProfile } from "@/features/settings/sample-profile";
import { navigationItem } from "@/lib/navigation";

const page = navigationItem("/settings");

export const metadata: Metadata = {
  title: page.label,
  description: page.description,
};

export default function SettingsPage() {
  return (
    <div className="flex flex-col gap-4">
      <AppearanceForm />
      <SampleProfile />
      <EmptyState
        icon={Settings}
        title="Household settings are not saved yet"
        description="Distribution company, tariff, and notification preferences will be stored in a later stage. The theme above stays on this device only."
      />
    </div>
  );
}
