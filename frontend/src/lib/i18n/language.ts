export const LANGUAGE_STORAGE_KEY = "bijlibachat.language.v1";

export const languages = ["en", "ur"] as const;

export type Language = (typeof languages)[number];

export type TextDirection = "ltr" | "rtl";

export function isLanguage(value: unknown): value is Language {
  return value === "en" || value === "ur";
}

export function directionFor(language: Language): TextDirection {
  return language === "ur" ? "rtl" : "ltr";
}

/**
 * Accepts the stored JSON string, a raw language name, or `{ language }`.
 * Anything else is English, and `recognized` is false so the caller can drop it.
 */
export function readLanguageValue(raw: string | null): {
  language: Language;
  recognized: boolean;
} {
  if (raw === null || raw === "") {
    return { language: "en", recognized: true };
  }

  if (isLanguage(raw)) {
    return { language: raw, recognized: true };
  }

  try {
    const parsed: unknown = JSON.parse(raw);
    if (isLanguage(parsed)) {
      return { language: parsed, recognized: true };
    }
    if (parsed && typeof parsed === "object" && "language" in parsed) {
      const language = (parsed as { language?: unknown }).language;
      if (isLanguage(language)) {
        return { language, recognized: true };
      }
    }
  } catch {
    return { language: "en", recognized: false };
  }

  return { language: "en", recognized: false };
}

export function serializeLanguage(language: Language): string {
  return JSON.stringify(language);
}

export function applyLanguage(
  language: Language,
  root: { lang: string; dir: string },
): void {
  root.lang = language;
  root.dir = directionFor(language);
}

/**
 * Runs in the document head before first paint.
 * Only English and Urdu are accepted. A bad value is removed and English is used.
 * The theme key is never read or written here.
 */
export const languageInitScript = `(function(){try{var k=${JSON.stringify(LANGUAGE_STORAGE_KEY)};var raw=localStorage.getItem(k);var lang="en";if(raw){var parsed=JSON.parse(raw);var value=typeof parsed==="string"?parsed:(parsed&&parsed.language);if(value==="ur")lang="ur";else if(value!=="en")localStorage.removeItem(k);}document.documentElement.lang=lang;document.documentElement.dir=lang==="ur"?"rtl":"ltr";}catch(e){try{localStorage.removeItem(${JSON.stringify(LANGUAGE_STORAGE_KEY)});}catch(e2){}document.documentElement.lang="en";document.documentElement.dir="ltr";}})();`;
