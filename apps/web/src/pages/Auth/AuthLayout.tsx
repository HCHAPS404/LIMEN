import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { HorizonField } from "../../components/atmosphere/HorizonField";
import { LimenMark, LimenWordmark } from "../../components/brand/Logo";
import { LanguageSwitcher } from "../../components/shell/LanguageSwitcher";
import { ThemeToggle } from "../../components/shell/ThemeToggle";

/** Form-level failure. Stated as text, never as border colour alone. */
export function AuthError({ message }: { message: string }) {
  return (
    <p
      role="alert"
      className="type-body-s m-0 rounded-sm border border-[color-mix(in_oklab,var(--limen-coral)_34%,transparent)] bg-[color-mix(in_oklab,var(--limen-coral)_9%,transparent)] px-3.5 py-3 text-coral"
    >
      {message}
    </p>
  );
}

/** Shared frame for sign in and sign up: brand on the left, the form on the
 *  right. The panel exists because it contains the interaction. */
export function AuthLayout({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
}) {
  const { t } = useTranslation("auth");

  return (
    <div className="relative flex min-h-dvh flex-col overflow-hidden">
      <HorizonField />

      <header className="relative z-[1] flex items-center justify-between gap-4 px-6 py-5 md:px-10">
        <Link to="/" aria-label="LIMEN" className="inline-flex items-center gap-2.5">
          <LimenMark size={18} />
          <LimenWordmark size="sm" className="tracking-[0.28em]" />
        </Link>
        <div className="flex items-center gap-2">
          <LanguageSwitcher />
          <ThemeToggle />
        </div>
      </header>

      <div className="relative z-[1] mx-auto grid w-full max-w-6xl flex-1 items-center gap-14 px-6 pb-16 md:px-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,26rem)] lg:gap-20">
        <div className="hidden flex-col lg:flex">
          <p className="type-eyebrow m-0 text-text-3">{t("brandLine")}</p>
          <h2 className="type-h1 mt-5 max-w-[22ch] text-ice">
            {t("aside.title")}
          </h2>
          <p className="type-body-l mt-5 max-w-[42ch] text-text-2">
            {t("aside.body")}
          </p>
        </div>

        <section className="glass-1 sheen-top w-full rounded-lg p-7 md:p-9">
          <div className="relative z-[1]">
            <h1 className="type-h2 m-0 text-ice">{title}</h1>
            <p className="type-body mt-3 text-text-2">{subtitle}</p>
            <div className="mt-8">{children}</div>
            <div className="mt-7 border-t border-glass-border pt-5">
              {footer}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
