import type { Metadata } from "next";
import { CliffGuardView } from "@/features/meter/cliff-guard-view";
import { navigationItem } from "@/lib/navigation";

const page = navigationItem("/cliff-guard");

export const metadata: Metadata = {
  title: page.label,
  description: page.description,
};

export default function CliffGuardPage() {
  return <CliffGuardView />;
}
