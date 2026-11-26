"use client";

import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";

export default function ErrorPage({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <EmptyState
      icon={AlertTriangle}
      title="This screen could not be loaded"
      description="The page failed before it could be shown. Nothing about a household bill was changed."
      action={
        <Button type="button" variant="secondary" onClick={() => reset()}>
          Try again
        </Button>
      }
    />
  );
}
