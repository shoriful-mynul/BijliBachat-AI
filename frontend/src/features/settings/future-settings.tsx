"use client";

import { useI18n } from "@/components/i18n/language-provider";
import { Badge } from "@/components/ui/badge";
import type { MessageKey } from "@/lib/i18n/messages";
import { Card } from "@/components/ui/card";
import { SectionHeader } from "@/components/ui/section-header";

const laterSections: readonly { title: MessageKey; description: MessageKey }[] = [
  { title: "settings.householdTitle", description: "settings.householdDescription" },
  { title: "settings.tariffTitle", description: "settings.tariffDescription" },
  { title: "settings.notificationsTitle", description: "settings.notificationsDescription" },
];

export function FutureSettings() {
  const { t } = useI18n();
  return (
    <section aria-labelledby="later-settings" className="flex flex-col gap-4">
      <div>
        <h2 id="later-settings" className="font-display text-base font-semibold leading-snug">
          {t("settings.laterTitle")}
        </h2>
        <p className="mt-1 max-w-2xl text-sm leading-6 text-muted">{t("settings.laterDescription")}</p>
      </div>
      {laterSections.map((section) => (
        <Card key={section.title} as="section">
          <SectionHeader
            as="h3"
            title={t(section.title)}
            description={t(section.description)}
            actions={<Badge>{t("settings.notYet")}</Badge>}
          />
        </Card>
      ))}
    </section>
  );
}
