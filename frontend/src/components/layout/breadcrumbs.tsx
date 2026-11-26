"use client";

import Link from "next/link";
import { useI18n } from "@/components/i18n/language-provider";
import type { NavigationItem } from "@/lib/navigation";

export function Breadcrumbs({ current }: { current: NavigationItem | null }) {
  const { t } = useI18n();
  if (!current || current.href === "/dashboard") {
    return null;
  }

  return (
    <nav aria-label={t("shell.breadcrumb")} className="mb-1 hidden md:block">
      <ol className="flex items-center gap-2 text-xs text-muted">
        <li>
          <Link href="/dashboard" className="rounded-md hover:text-foreground">
            {t("shell.homeCrumb")}
          </Link>
        </li>
        <li aria-hidden="true">/</li>
        <li aria-current="page" className="text-foreground">
          {t(current.labelKey)}
        </li>
      </ol>
    </nav>
  );
}
