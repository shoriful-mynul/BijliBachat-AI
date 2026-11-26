"use client";

import type { ReactNode } from "react";
import { useI18n } from "@/components/i18n/language-provider";
import { AppHeader } from "@/components/layout/app-header";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { MobileNavigation } from "@/components/layout/mobile-navigation";
import { PageContainer } from "@/components/layout/page-container";
import { ServiceStatus } from "@/components/layout/service-status";

export function AppShell({ children }: { children: ReactNode }) {
  const { t } = useI18n();

  return (
    <div className="flex min-h-dvh bg-background text-foreground">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:top-3 focus:start-3 focus:z-50 focus:rounded-xl focus:bg-card focus:px-4 focus:py-3 focus:text-sm focus:font-semibold"
      >
        {t("shell.skip")}
      </a>
      <AppSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <AppHeader />
        <main id="main" className="flex-1 px-4 py-5 pb-28 md:px-8 md:py-8 md:pb-8">
          <PageContainer>
            {children}
            <ServiceStatus />
          </PageContainer>
        </main>
      </div>
      <MobileNavigation />
    </div>
  );
}
