import type { Metadata } from "next";
import { OverviewDashboard } from "@/features/overview/overview-dashboard";
import { navigationItem } from "@/lib/navigation";

const page = navigationItem("/");

export const metadata: Metadata = {
  title: page.label,
  description: page.description,
};

export default function OverviewPage() {
  return <OverviewDashboard />;
}
