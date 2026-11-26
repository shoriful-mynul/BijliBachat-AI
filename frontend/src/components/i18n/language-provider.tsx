"use client";

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import {
  applyLanguage,
  isLanguage,
  LANGUAGE_STORAGE_KEY,
  readLanguageValue,
  serializeLanguage,
  type Language,
} from "@/lib/i18n/language";
import {
  messageKeyForEnglish,
  translate,
  type MessageKey,
} from "@/lib/i18n/messages";

type LanguageContextValue = {
  language: Language;
  direction: "ltr" | "rtl";
  setLanguage: (language: Language) => void;
  t: (key: MessageKey, values?: Record<string, string | number>) => string;
  text: (value: string | null | undefined) => string;
};

const LanguageContext = createContext<LanguageContextValue | null>(null);
const languageChangeEvent = "bb-language-change";

function subscribe(onStoreChange: () => void) {
  window.addEventListener(languageChangeEvent, onStoreChange);
  return () => window.removeEventListener(languageChangeEvent, onStoreChange);
}

function getSnapshot(): Language {
  const value = document.documentElement.lang;
  return isLanguage(value) ? value : "en";
}

function getServerSnapshot(): Language {
  return "en";
}

function writeLanguage(language: Language) {
  applyLanguage(language, document.documentElement);
  try {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, serializeLanguage(language));
  } catch {
    // The choice still applies for this view when storage is blocked.
  }
  window.dispatchEvent(new Event(languageChangeEvent));
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const language = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const announced = useRef(false);
  const liveRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    try {
      const stored = readLanguageValue(localStorage.getItem(LANGUAGE_STORAGE_KEY));
      if (!stored.recognized) {
        localStorage.removeItem(LANGUAGE_STORAGE_KEY);
        writeLanguage("en");
        return;
      }
      if (document.documentElement.lang !== stored.language) {
        writeLanguage(stored.language);
      }
    } catch {
      writeLanguage("en");
    }
  }, []);

  useEffect(() => {
    if (!announced.current) {
      announced.current = true;
      return;
    }
    if (liveRef.current) {
      liveRef.current.textContent = translate(language, "shell.languageChanged", {
        language: translate(language, language === "ur" ? "settings.urdu" : "settings.english"),
      });
    }
  }, [language]);

  const setLanguage = (next: Language) => {
    writeLanguage(next);
  };

  const value: LanguageContextValue = {
    language,
    direction: language === "ur" ? "rtl" : "ltr",
    setLanguage,
    t: (key, values) => translate(language, key, values),
    text: (raw) => {
      if (!raw) {
        return "";
      }
      const key = messageKeyForEnglish(raw);
      return key ? translate(language, key) : raw;
    },
  };

  return (
    <LanguageContext.Provider value={value}>
      <div ref={liveRef} className="sr-only" role="status" aria-live="polite" />
      {children}
    </LanguageContext.Provider>
  );
}

export function useI18n(): LanguageContextValue {
  const value = useContext(LanguageContext);
  if (!value) {
    throw new Error("useI18n must be used within LanguageProvider");
  }
  return value;
}
