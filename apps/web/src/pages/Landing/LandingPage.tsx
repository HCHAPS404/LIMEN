import { motion } from "framer-motion";
import {
  ArrowRight,
  Database,
  FileMinus2,
  Lock,
  Mic,
  ShieldCheck,
  Users,
  Waypoints,
} from "lucide-react";
import type { ComponentType, ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { useAuth } from "../../app/providers/AuthProvider";
import { HorizonField } from "../../components/atmosphere/HorizonField";
import {
  LimenLockup,
  LimenMark,
  LimenWordmark,
} from "../../components/brand/Logo";
import { Button } from "../../components/primitives/Button";
import { LanguageSwitcher } from "../../components/shell/LanguageSwitcher";
import { ThemeToggle } from "../../components/shell/ThemeToggle";
import { useLandingVoiceField } from "../../features/call-session/useLandingVoiceField";
import { VoiceOrb } from "../../features/call-session/VoiceOrb";
import { cn } from "../../lib/cn";

/** Shared landing column — nav, hero, and body sections share this width. */
const SHELL = "mx-auto w-full max-w-[72rem]";

const ease = [0.22, 0.61, 0.36, 1] as const;

const rise = (delay: number) => ({
  initial: { opacity: 0, y: 18 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.65, delay, ease },
});

const reveal = (delay = 0) => ({
  initial: { opacity: 0, y: 16 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, amount: 0.25 },
  transition: { duration: 0.5, delay, ease },
});

type IconType = ComponentType<{
  size?: number;
  strokeWidth?: number;
  className?: string;
  "aria-hidden"?: boolean;
}>;

const pillars = [
  { key: "voice", icon: Mic as IconType },
  { key: "evidence", icon: Database as IconType },
  { key: "safety", icon: ShieldCheck as IconType },
  { key: "traza", icon: Waypoints as IconType },
] as const;

const steps = ["one", "two", "three"] as const;

const guarantees = [
  { key: "isolation", icon: Users as IconType },
  { key: "session", icon: Lock as IconType },
  { key: "deletion", icon: FileMinus2 as IconType },
] as const;

function Shell({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={cn(SHELL, className)}>{children}</div>;
}

export function LandingPage() {
  const { t } = useTranslation("landing");
  const { status } = useAuth();
  const signedIn = status === "authenticated";
  const voice = useLandingVoiceField();

  return (
    <div className="relative min-h-dvh overflow-x-hidden">
      <HorizonField />

      <div className="relative z-[1]">
        <LandingNav signedIn={signedIn} />

        <main className="w-full px-4 pb-16 pt-2 sm:px-6 md:px-8">
          {/* Hero */}
          <section
            className="relative flex min-h-[min(76vh,40rem)] items-center pb-14 pt-6 md:pb-16 md:pt-8"
            aria-label={t("nav.home")}
          >
            <Shell className="grid items-center gap-8 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)] lg:gap-12">
              <div className="relative z-[1] flex flex-col gap-4 md:gap-5">
                <motion.div {...rise(0.04)}>
                  <LimenWordmark
                    size="xl"
                    className="text-riser max-w-full text-left text-[clamp(2.5rem,6.5vw,4.75rem)] leading-none tracking-[0.1em]"
                  />
                </motion.div>

                <motion.h1
                  {...rise(0.1)}
                  className="type-h1 m-0 max-w-[24ch] text-ice md:text-[clamp(1.75rem,2.4vw,2.35rem)]"
                >
                  {t("hero.headline")}
                </motion.h1>

                <motion.p
                  {...rise(0.16)}
                  className="type-body m-0 max-w-[42ch] text-text-2 md:text-[1.0625rem] md:leading-relaxed"
                >
                  {t("hero.support")}
                </motion.p>

                <motion.div
                  {...rise(0.22)}
                  className="mt-1 flex flex-col gap-3 sm:flex-row sm:items-center"
                >
                  {signedIn ? (
                    <Button
                      variant="inverse"
                      size="lg"
                      asChild
                      icon={
                        <ArrowRight aria-hidden size={17} strokeWidth={1.75} />
                      }
                    >
                      <Link to="/call">{t("nav.enter")}</Link>
                    </Button>
                  ) : (
                    <>
                      <Button
                        variant="inverse"
                        size="lg"
                        asChild
                        icon={
                          <ArrowRight
                            aria-hidden
                            size={17}
                            strokeWidth={1.75}
                          />
                        }
                      >
                        <Link to="/register">{t("nav.signUp")}</Link>
                      </Button>
                      <Button variant="secondary" size="lg" asChild>
                        <Link to="/login">{t("nav.signIn")}</Link>
                      </Button>
                    </>
                  )}
                </motion.div>
              </div>

              <motion.div
                {...rise(0.12)}
                className="relative z-[1] flex flex-col items-center justify-center gap-4 lg:items-end lg:justify-end"
              >
                <VoiceOrb
                  phase={voice.phase}
                  level={voice.level}
                  className="h-[clamp(17rem,44vh,30rem)] w-[clamp(17rem,44vh,30rem)]"
                />
                {!voice.enabled && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={voice.enable}
                    className="relative z-[1]"
                  >
                    {t("hero.enableMic")}
                  </Button>
                )}
              </motion.div>
            </Shell>
          </section>

          {/* Problem */}
          <section className="border-t border-glass-border py-16 md:py-20">
            <Shell>
              <motion.div
                {...reveal()}
                className="grid gap-6 md:grid-cols-[minmax(0,0.32fr)_minmax(0,0.68fr)] md:items-start md:gap-12"
              >
                <p className="type-eyebrow m-0 text-text-3">
                  {t("problem.eyebrow")}
                </p>
                <div>
                  <h2 className="type-h1 m-0 max-w-[26ch] text-ice">
                    {t("problem.title")}
                  </h2>
                  <p className="type-body-l mt-5 max-w-none text-text-2 md:max-w-[54ch]">
                    {t("problem.body")}
                  </p>
                </div>
              </motion.div>
            </Shell>
          </section>

          {/* How it works */}
          <section
            id="how-it-works"
            className="scroll-mt-28 border-t border-glass-border py-16 md:py-20"
          >
            <Shell>
              <motion.div
                {...reveal()}
                className="grid gap-4 md:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] md:items-end md:gap-10"
              >
                <div>
                  <p className="type-eyebrow m-0 text-text-3">
                    {t("steps.eyebrow")}
                  </p>
                  <h2 className="type-h1 mt-3 text-ice">{t("steps.title")}</h2>
                </div>
                <p className="type-body m-0 text-text-2 md:pb-1">
                  {t("steps.lead")}
                </p>
              </motion.div>

              <ol className="mt-10 grid list-none gap-8 border-t border-glass-border p-0 pt-10 sm:grid-cols-2 lg:mt-12 lg:grid-cols-3 lg:gap-10">
                {steps.map((step, index) => (
                  <motion.li
                    key={step}
                    {...reveal(index * 0.06)}
                    className="flex flex-col gap-3"
                  >
                    <span className="type-metric text-[1.25rem] text-text-3">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <h3 className="type-h3 m-0 text-ice">
                      {t(`steps.${step}.title`)}
                    </h3>
                    <p className="type-body m-0 text-text-2">
                      {t(`steps.${step}.body`)}
                    </p>
                  </motion.li>
                ))}
              </ol>
            </Shell>
          </section>

          {/* Pillars */}
          <section className="border-t border-glass-border py-16 md:py-20">
            <Shell>
              <motion.div
                {...reveal()}
                className="grid gap-4 md:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)] md:items-end md:gap-10"
              >
                <div>
                  <p className="type-eyebrow m-0 text-text-3">
                    {t("pillars.eyebrow")}
                  </p>
                  <h2 className="type-h1 mt-3 max-w-[24ch] text-ice">
                    {t("pillars.title")}
                  </h2>
                </div>
                <p className="type-body m-0 text-text-2 md:pb-1">
                  {t("pillars.lead")}
                </p>
              </motion.div>

              <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:mt-12 lg:grid-cols-4 lg:gap-5">
                {pillars.map(({ key, icon: Icon }, index) => (
                  <motion.article
                    key={key}
                    {...reveal(index * 0.05)}
                    className="glass-1 sheen-top flex flex-col gap-4 rounded-2xl p-5 md:p-6"
                  >
                    <div className="relative z-[1] flex items-center gap-3">
                      <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-glass-border bg-[var(--glass-highlight)]">
                        <Icon
                          aria-hidden
                          size={17}
                          strokeWidth={1.6}
                          className="text-ice"
                        />
                      </span>
                      <h3 className="type-label m-0 text-ice">
                        {t(`pillars.${key}.name`)}
                      </h3>
                    </div>
                    <p className="type-body relative z-[1] m-0 text-text-2">
                      {t(`pillars.${key}.body`)}
                    </p>
                  </motion.article>
                ))}
              </div>
            </Shell>
          </section>

          {/* Security */}
          <section
            id="security"
            className="scroll-mt-28 border-t border-glass-border py-16 md:py-20"
          >
            <Shell className="grid gap-10 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] lg:gap-14">
              <motion.div {...reveal()}>
                <p className="type-eyebrow m-0 text-text-3">
                  {t("security.eyebrow")}
                </p>
                <h2 className="type-h1 mt-3 max-w-[20ch] text-ice">
                  {t("security.title")}
                </h2>
                <p className="type-body-l mt-5 max-w-[42ch] text-text-2">
                  {t("security.lead")}
                </p>
              </motion.div>

              <motion.dl {...reveal(0.06)} className="m-0 flex flex-col gap-8">
                {guarantees.map(({ key, icon: Icon }) => (
                  <div key={key} className="flex gap-4">
                    <span className="mt-0.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-glass-border bg-[var(--glass-highlight)]">
                      <Icon
                        aria-hidden
                        size={16}
                        strokeWidth={1.6}
                        className="text-ice"
                      />
                    </span>
                    <div className="flex flex-col gap-1.5">
                      <dt className="type-h3 m-0 text-[1.0625rem] text-ice">
                        {t(`security.${key}.title`)}
                      </dt>
                      <dd className="type-body m-0 text-text-2">
                        {t(`security.${key}.body`)}
                      </dd>
                    </div>
                  </div>
                ))}
              </motion.dl>
            </Shell>
          </section>

          {/* Status */}
          <section className="border-t border-glass-border py-14 md:py-16">
            <Shell>
              <motion.div
                {...reveal()}
                className="grid gap-4 md:grid-cols-[minmax(0,0.28fr)_minmax(0,0.72fr)] md:items-baseline md:gap-10"
              >
                <p className="type-eyebrow m-0 text-text-3">
                  {t("status.eyebrow")}
                </p>
                <div>
                  <h2 className="type-h2 m-0 text-ice">{t("status.title")}</h2>
                  <p className="type-body mt-4 max-w-[56ch] text-text-2">
                    {t("status.body")}
                  </p>
                </div>
              </motion.div>
            </Shell>
          </section>

          {/* Closing CTA */}
          <section className="pb-6 pt-2 md:pb-8">
            <Shell>
              <motion.div
                {...reveal()}
                className="glass-2 sheen-top relative flex flex-col gap-6 overflow-hidden rounded-2xl px-7 py-10 md:flex-row md:items-center md:justify-between md:gap-10 md:px-10 md:py-12"
              >
                <div className="relative z-[1] max-w-xl">
                  <h2 className="type-h1 m-0 text-ice">{t("cta.title")}</h2>
                  <p className="type-body mt-4 text-text-2">{t("cta.body")}</p>
                </div>
                <div className="relative z-[1] flex shrink-0 flex-col gap-3 sm:flex-row">
                  <Button
                    variant="inverse"
                    size="lg"
                    asChild
                    icon={
                      <ArrowRight aria-hidden size={17} strokeWidth={1.75} />
                    }
                  >
                    <Link to={signedIn ? "/call" : "/register"}>
                      {signedIn ? t("nav.enter") : t("nav.signUp")}
                    </Link>
                  </Button>
                  {!signedIn && (
                    <Button variant="secondary" size="lg" asChild>
                      <Link to="/login">{t("nav.signIn")}</Link>
                    </Button>
                  )}
                </div>
              </motion.div>
            </Shell>
          </section>

          <footer className="border-t border-glass-border pt-10 md:pt-12">
            <Shell className="flex flex-col gap-8 md:flex-row md:items-end md:justify-between">
              <div className="flex flex-col gap-3">
                <LimenLockup />
                <p className="type-body-s m-0 max-w-[44ch] text-text-3">
                  {t("footer.tagline")}
                </p>
              </div>
              <div className="flex flex-col items-start gap-3 md:items-end">
                <div className="flex flex-wrap gap-5">
                  <a
                    href="#how-it-works"
                    className="type-body-s text-text-2 transition-colors hover:text-ice"
                  >
                    {t("nav.howItWorks")}
                  </a>
                  <a
                    href="#security"
                    className="type-body-s text-text-2 transition-colors hover:text-ice"
                  >
                    {t("nav.security")}
                  </a>
                  <Link
                    to="/login"
                    className="type-body-s text-text-2 transition-colors hover:text-ice"
                  >
                    {t("nav.signIn")}
                  </Link>
                </div>
                <p className="type-body-s m-0 text-text-3">
                  {t("footer.license")}
                </p>
              </div>
            </Shell>
          </footer>
        </main>
      </div>
    </div>
  );
}

function LandingNav({ signedIn }: { signedIn: boolean }) {
  const { t } = useTranslation("landing");

  return (
    <header className="sticky top-0 z-40 px-4 pt-4 sm:px-6 md:px-8 md:pt-5">
      <div
        className={cn(
          SHELL,
          "glass-2 sheen-top flex h-14 items-center gap-2 rounded-2xl px-3 sm:gap-3 sm:px-4",
        )}
      >
        <Link
          to="/"
          aria-label={t("nav.home")}
          className="relative z-[1] mr-auto inline-flex shrink-0 items-center gap-2.5"
        >
          <LimenMark size={16} />
          <LimenWordmark size="sm" className="tracking-[0.28em]" />
        </Link>

        <nav
          aria-label={t("nav.howItWorks")}
          className="relative z-[1] hidden items-center gap-5 lg:flex"
        >
          <a
            href="#how-it-works"
            className="type-body-s text-text-2 transition-colors hover:text-ice"
          >
            {t("nav.howItWorks")}
          </a>
          <a
            href="#security"
            className="type-body-s text-text-2 transition-colors hover:text-ice"
          >
            {t("nav.security")}
          </a>
        </nav>

        <div className="relative z-[1] flex items-center gap-1">
          <LanguageSwitcher />
          <ThemeToggle />
        </div>

        {signedIn ? (
          <Button variant="inverse" size="sm" asChild className="relative z-[1]">
            <Link to="/call">{t("nav.enter")}</Link>
          </Button>
        ) : (
          <div className="relative z-[1] flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              asChild
              className="hidden sm:flex"
            >
              <Link to="/login">{t("nav.signIn")}</Link>
            </Button>
            <Button variant="inverse" size="sm" asChild>
              <Link to="/register">{t("nav.signUp")}</Link>
            </Button>
          </div>
        )}
      </div>
    </header>
  );
}
