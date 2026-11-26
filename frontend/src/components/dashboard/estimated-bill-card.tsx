import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { DataTrustChip } from "@/components/ui/data-trust-chip";
import { SectionHeader } from "@/components/ui/section-header";
import { demoOverview } from "@/features/overview/demo-data";
import { formatPkr } from "@/lib/format";

export function EstimatedBillCard() {
  return (
    <Card className="h-full shadow-[inset_3px_0_0_#42c8e8]">
      <SectionHeader
        title="Estimated monthly bill"
        description="An example projection for the sample cycle. The billing engine is not connected."
        actions={
          <>
            <Badge>Demo data</Badge>
            <DataTrustChip status="estimated" />
          </>
        }
      />
      <p className="mt-5 font-display text-4xl font-semibold tracking-tight tabular-nums">
        {formatPkr(demoOverview.bill.amountPkr)}
      </p>
      <p className="mt-3 max-w-xl text-sm leading-6 text-muted">
        Illustrative figure for {demoOverview.cycle.label}. This amount is not
        calculated from the units below, and it is not a quotation from a
        distribution company.
      </p>
    </Card>
  );
}
