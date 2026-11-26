import type { Metadata } from "next";
import { BillAuditor } from "@/features/bill-auditor/bill-auditor";
import { navigationItem } from "@/lib/navigation";

const page = navigationItem("/bill-auditor");

export const metadata: Metadata = {
  title: page.label,
  description: page.description,
};

export default function BillAuditorPage() {
  return <BillAuditor />;
}
