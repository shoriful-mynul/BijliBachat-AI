import type { Metadata } from "next";
import { History } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { navigationItem } from "@/lib/navigation";

const page = navigationItem("/history");

export const metadata: Metadata = {
  title: page.label,
  description: page.description,
};

export default function HistoryPage() {
  return (
    <EmptyState
      icon={History}
      title="History is not available yet"
      description="Earlier billing cycles will appear here after readings are stored. Nothing is stored in this version."
    />
  );
}
