"use client";

import { AlertTriangle } from "lucide-react";
import { useI18n } from "@/components/i18n/language-provider";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";

export default function ErrorPage({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const { t } = useI18n();
  return (
    <EmptyState
      icon={AlertTriangle}
      title={t("error.title")}
      description={t("error.description")}
      action={
        <Button type="button" variant="secondary" onClick={() => reset()}>
          {t("error.retry")}
        </Button>
      }
    />
  );
}
