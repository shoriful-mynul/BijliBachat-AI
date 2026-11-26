import { Compass } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";

export default function NotFound() {
  return (
    <EmptyState
      icon={Compass}
      title="This page is not part of BijliBachat"
      description="The address does not match a section of the app. Overview is the place to start."
      action={
        <Button href="/dashboard" variant="primary">
          Back to overview
        </Button>
      }
    />
  );
}
