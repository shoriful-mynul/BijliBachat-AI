import type { Metadata } from "next";
import { PredictionView } from "@/features/prediction/prediction-view";
import { navigationItem } from "@/lib/navigation";

const page = navigationItem("/prediction");

export const metadata: Metadata = {
  title: page.label,
  description: page.description,
};

export default function PredictionPage() {
  return <PredictionView />;
}
