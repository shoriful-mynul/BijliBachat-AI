import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { SectionHeader } from "@/components/ui/section-header";

const laterSections = [
  {
    title: "Household",
    description:
      "A name, a place, and who shares the bill will be saved here later. This version does not store a household.",
  },
  {
    title: "Electricity tariff",
    description:
      "A distribution company and a dated tariff will be chosen here later. No tariff is loaded in this version.",
  },
  {
    title: "Notifications",
    description:
      "Alerts are not sent in this version. Delivery choices will live here once that exists.",
  },
] as const;

export function FutureSettings() {
  return (
    <section aria-labelledby="later-settings" className="flex flex-col gap-4">
      <div>
        <h2 id="later-settings" className="font-display text-base font-semibold leading-snug">
          Not saved yet
        </h2>
        <p className="mt-1 max-w-2xl text-sm leading-6 text-muted">
          These sections are named so you know where they will live. None of them work in this version.
        </p>
      </div>
      {laterSections.map((section) => (
        <Card key={section.title} as="section">
          <SectionHeader
            as="h3"
            title={section.title}
            description={section.description}
            actions={<Badge>Not available yet</Badge>}
          />
        </Card>
      ))}
    </section>
  );
}
