"use client";

import type { ReactNode } from "react";
import { useI18n } from "@/components/i18n/language-provider";

/** Translates a known interface sentence and isolates an English API sentence in Urdu. */
export function LocalizedNotice({ value }: { value: string | null | undefined }) {
  const { text, language } = useI18n();
  if (!value) {
    return null;
  }
  const localized = text(value);
  if (language === "ur" && localized === value) {
    return (
      <bdi lang="en" dir="ltr">
        {value}
      </bdi>
    );
  }
  return <>{localized}</>;
}

/** Keeps an English API sentence readable inside Urdu RTL layout. */
export function SourceText({ children }: { children: ReactNode }) {
  const { language } = useI18n();
  if (language !== "ur" || children === null || children === undefined || children === "") {
    return <>{children}</>;
  }
  return (
    <bdi lang="en" dir="ltr">
      {children}
    </bdi>
  );
}
