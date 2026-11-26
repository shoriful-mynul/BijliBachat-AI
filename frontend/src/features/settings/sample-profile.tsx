import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { SectionHeader } from "@/components/ui/section-header";
import { demoOverview } from "@/features/overview/demo-data";

export function SampleProfile() {
  return (
    <Card>
      <SectionHeader
        title="Sample household"
        description="A read-only example so the form controls are visible. It is not saved."
      />
      <Input
        className="mt-4 max-w-sm"
        label="Place"
        value={`${demoOverview.household.place} — sample`}
        readOnly
        hint="Editing and storage arrive in a later stage."
      />
    </Card>
  );
}
