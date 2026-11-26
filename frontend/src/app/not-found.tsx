"use client";

import { Compass } from "lucide-react";
import { useI18n } from "@/components/i18n/language-provider";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";

export default function NotFound() {
  const { t } = useI18n();
  return (
    <EmptyState
      icon={Compass}
      title={t("notFound.title")}
      description={t("notFound.description")}
      action={
        <Button href="/dashboard" variant="primary">
          {t("notFound.action")}
        </Button>
      }
    />
  );
}
