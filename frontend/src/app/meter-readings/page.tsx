import type { Metadata } from "next";
import { MeterCapture } from "@/features/meter/meter-capture";
import { navigationItem } from "@/lib/navigation";

const page = navigationItem("/meter-readings");

export const metadata: Metadata = {
  title: page.label,
  description: page.description,
};

export default function MeterReadingsPage() {
  return <MeterCapture />;
}
