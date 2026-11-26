"use client";

import { Card } from "@/components/ui/card";
import { SectionHeader } from "@/components/ui/section-header";
import { Select } from "@/components/ui/select";
import { useI18n } from "@/components/i18n/language-provider";
import { isLanguage } from "@/lib/i18n/language";

export function LanguageForm() {
  const { language, setLanguage, t } = useI18n();
  const current = t(language === "ur" ? "settings.urdu" : "settings.english");

  return (
    <Card>
      <SectionHeader title={t("settings.languageTitle")} description={t("settings.languageDescription")} />
      <Select
        className="mt-4 max-w-sm"
        label={t("settings.languageLabel")}
        value={language}
        options={[
          { value: "en", label: t("settings.english") },
          { value: "ur", label: t("settings.urdu") },
        ]}
        hint={t("settings.languageHint")}
        onChange={(event) => {
          if (isLanguage(event.target.value)) {
            setLanguage(event.target.value);
          }
        }}
      />
      <p className="mt-3 text-sm leading-6" role="status">
        {t("settings.languageCurrent", { language: current })}
      </p>
    </Card>
  );
}
