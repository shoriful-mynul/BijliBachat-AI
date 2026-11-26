"use client";

import { useI18n } from "@/components/i18n/language-provider";
import { Card } from "@/components/ui/card";
import { SectionHeader } from "@/components/ui/section-header";
import { Select } from "@/components/ui/select";
import { useTheme } from "@/hooks/use-theme";
import { isTheme } from "@/lib/theme";

export function AppearanceForm() {
  const { theme, setTheme } = useTheme();
  const { t } = useI18n();
  const options = [
    { value: "dark", label: t("settings.themeDark") },
    { value: "light", label: t("settings.themeLight") },
  ] as const;

  return (
    <Card>
      <SectionHeader title={t("settings.appearanceTitle")} description={t("settings.appearanceDescription")} />
      <Select
        className="mt-4 max-w-sm"
        label={t("settings.themeLabel")}
        value={theme}
        options={options}
        hint={t("settings.themeHint")}
        onChange={(event) => {
          if (isTheme(event.target.value)) {
            setTheme(event.target.value);
          }
        }}
      />
    </Card>
  );
}
