import type { Metadata } from "next";
import { AppearanceForm } from "@/features/settings/appearance-form";
import { FutureSettings } from "@/features/settings/future-settings";
import { navigationItem } from "@/lib/navigation";

const page = navigationItem("/settings");

export const metadata: Metadata = {
  title: page.label,
  description: page.description,
};

export default function SettingsPage() {
  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <AppearanceForm />
      <FutureSettings />
    </div>
  );
}
