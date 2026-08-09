import { useTranslation } from "react-i18next";

import { SUPPORTED_LOCALES, setLocale, type Locale } from "../../i18n";
import { cn } from "../../lib/cn";

/** Two locales only, so a segmented control shows the current state without
 *  hiding it behind a menu. */
export function LanguageSwitcher({ className }: { className?: string }) {
  const { t, i18n } = useTranslation("common");
  const active = (i18n.resolvedLanguage ?? "es") as Locale;

  return (
    <div
      role="group"
      aria-label={t("language.label")}
      className={cn(
        "inline-flex items-center gap-0.5 rounded-sm border border-glass-border p-0.5",
        "bg-[var(--glass-surface)] backdrop-blur-[14px]",
        className,
      )}
    >
      {SUPPORTED_LOCALES.map((locale) => {
        const isActive = locale === active;
        return (
          <button
            key={locale}
            type="button"
            aria-pressed={isActive}
            onClick={() => void setLocale(locale)}
            className={cn(
              "rounded-xs px-2.5 py-1 text-[0.75rem] font-semibold tracking-[0.08em] uppercase",
              "transition-colors duration-[var(--motion-fast)] ease-[var(--motion-ease)]",
              isActive
                ? "bg-[var(--glass-highlight)] text-ice"
                : "text-text-3 hover:text-text-2",
            )}
          >
            {locale}
          </button>
        );
      })}
    </div>
  );
}
