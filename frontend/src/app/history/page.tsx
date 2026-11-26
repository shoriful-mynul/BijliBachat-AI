import type { Metadata } from "next";
import { HistoryView } from "@/features/history/history-view";
import { navigationItem } from "@/lib/navigation";

const page = navigationItem("/history");

export const metadata: Metadata = {
  title: page.label,
  description: page.description,
};

export default function HistoryPage() {
  return <HistoryView />;
}
