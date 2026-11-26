import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { NavigationItem } from "@/lib/navigation";

export function FeaturePlaceholder({ item }: { item: NavigationItem }) {
  if (item.status !== "placeholder") {
    throw new Error(`${item.href} is not a placeholder route`);
  }

  const Icon = item.icon;

  return (
    <Card as="section" className="max-w-2xl" aria-labelledby="feature-status">
      <div className="grid h-12 w-12 place-items-center rounded-xl bg-raised text-foreground">
        <Icon className="h-5 w-5" aria-hidden="true" />
      </div>
      <div className="mt-4">
        <Badge>Not available yet</Badge>
      </div>
      <h2 id="feature-status" className="mt-4 font-display text-lg font-semibold leading-snug">
        What this will do
      </h2>
      <p className="mt-2 max-w-xl text-sm leading-6 text-foreground">{item.purpose}</p>
      <p className="mt-2 max-w-xl text-sm leading-6 text-muted">{item.later}</p>
    </Card>
  );
}
