import type { Metadata } from "next";
import { FeaturePlaceholder } from "@/components/layout/feature-placeholder";
import { navigationItem } from "@/lib/navigation";

const page = navigationItem("/bill-auditor");

export const metadata: Metadata = {
  title: page.label,
  description: page.description,
};

export default function BillAuditorPage() {
  return <FeaturePlaceholder item={page} />;
}
