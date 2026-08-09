import i18next from "i18next";
import { initReactI18next } from "react-i18next";

import { en } from "./locales/en";
import { es } from "./locales/es";

export const SUPPORTED_LOCALES = ["es", "en"] as const;
export type Locale = (typeof SUPPORTED_LOCALES)[number];

export const LOCALE_STORAGE_KEY = "limen.locale";
/** Spanish first: the patient-facing voice loop is Spanish. */
export const DEFAULT_LOCALE: Locale = "es";

export const NAMESPACES = [
  "common",
  "shell",
  "landing",
  "auth",
  "call",
  "knowledge",
  "trace",
  "sessions",
  "connection",
] as const;

function isLocale(value: string | null): value is Locale {
  return value === "es" || value === "en";
}

export function readStoredLocale(): Locale {
  try {
    const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY);
    return isLocale(stored) ? stored : DEFAULT_LOCALE;
  } catch {
    return DEFAULT_LOCALE;
  }
}

const initialLocale =
  typeof window === "undefined" ? DEFAULT_LOCALE : readStoredLocale();

void i18next.use(initReactI18next).init({
  resources: { es, en },
  lng: initialLocale,
  fallbackLng: DEFAULT_LOCALE,
  supportedLngs: SUPPORTED_LOCALES,
  ns: NAMESPACES,
  defaultNS: "common",
  // React already escapes interpolated values.
  interpolation: { escapeValue: false },
  returnNull: false,
});

export async function setLocale(locale: Locale): Promise<void> {
  await i18next.changeLanguage(locale);
  document.documentElement.lang = locale;
  try {
    window.localStorage.setItem(LOCALE_STORAGE_KEY, locale);
  } catch {
    // Preference stays session-only when storage is unavailable.
  }
}

export function currentLocale(): Locale {
  return isLocale(i18next.resolvedLanguage ?? null)
    ? (i18next.resolvedLanguage as Locale)
    : DEFAULT_LOCALE;
}

export default i18next;
