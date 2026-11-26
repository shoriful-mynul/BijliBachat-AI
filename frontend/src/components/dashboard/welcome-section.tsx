import { Badge } from "@/components/ui/badge";
import { demoOverview } from "@/features/overview/demo-data";

export function WelcomeSection() {
  const { household, cycle } = demoOverview;

  return (
    <section aria-labelledby="welcome-title">
      <p className="text-sm text-muted">
        Sample household · {household.place}
      </p>
      <h2
        id="welcome-title"
        className="mt-1 font-display text-2xl font-semibold tracking-tight"
      >
        Assalam o Alaikum, {household.greetingName}
      </h2>
      <p className="mt-2">
        <span lang="ur" dir="rtl" className="inline-block font-urdu text-xl leading-[2.6]">
          {household.urduTagline}
        </span>
      </p>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
        This is the fictional {household.place} household for {cycle.label}. The
        page shows how a month will be organized. It is not your bill, and it is
        not a live meter reading.
      </p>
      <div className="mt-3">
        <Badge>Demo data</Badge>
      </div>
    </section>
  );
}
