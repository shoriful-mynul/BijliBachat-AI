"use client";

import { useI18n } from "@/components/i18n/language-provider";
import { LoadingState } from "@/components/ui/loading-state";

export default function Loading() {
  const { t } = useI18n();
  return <LoadingState label={t("loading.page")} />;
}
