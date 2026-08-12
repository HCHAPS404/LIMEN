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
  initial: { opacity: 0, y: 22 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.7, delay, ease },
});

const reveal = (delay = 0) => ({
  initial: { opacity: 0, y: 20 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, amount: 0.22 },
  transition: { duration: 0.55, delay, ease },
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

const tileClass = cn(
  "rounded-xl border border-[color-mix(in_oklab,var(--limen-ice)_18%,transparent)]",
  "bg-[var(--glass-surface)] backdrop-blur-[18px]",
  "shadow-[var(--shadow-panel)]",
  "transition-[transform,border-color,box-shadow] duration-[var(--motion-base)] ease-[var(--motion-ease)]",
  "hover:-translate-y-0.5 hover:border-[color-mix(in_oklab,var(--limen-cyan)_32%,transparent)]",
  "hover:shadow-[var(--shadow-float)]",
);

function Shell({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={cn(SHELL, className)}>{children}</div>;
}

/** Icon well with a quiet cyan→teal rim — clinical glass, not neon chrome. */
function FeatureIcon({
  icon: Icon,
  size = "lg",
}: {
  icon: IconType;
  size?: "md" | "lg";
}) {
  const box = size === "lg" ? "h-16 w-16" : "h-12 w-12";
  const glyph = size === "lg" ? 28 : 22;

  return (
    <span
      className={cn(
        "relative inline-flex shrink-0 items-center justify-center rounded-lg",
        box,
      )}
      style={{
        background: `
          linear-gradient(
            145deg,
            color-mix(in oklab, var(--limen-bg-2) 70%, transparent),
            color-mix(in oklab, var(--limen-bg-3) 55%, transparent)
          )
        `,
        boxShadow: `
          inset 0 1px 0 color-mix(in oklab, var(--limen-ice) 12%, transparent),
          0 0 0 1px color-mix(in oklab, var(--limen-cyan) 28%, transparent),
          0 0 24px color-mix(in oklab, var(--limen-action) 12%, transparent)
        `,
      }}
    >
      <span
        aria-hidden
        className="pointer-events-none absolute inset-[1px] rounded-[calc(var(--radius-md)-1px)]"
        style={{
          background: `linear-gradient(
            135deg,
            color-mix(in oklab, var(--limen-cyan) 22%, transparent),
            transparent 42%,
            color-mix(in oklab, var(--limen-teal) 18%, transparent)
          )`,
          opacity: 0.55,
        }}
      />
      <Icon
        aria-hidden
        size={glyph}
        strokeWidth={1.5}
        className="relative z-[1] text-cyan"
      />
    </span>
  );
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
          {/* Hero — brand + claim left, voice sphere right (fills the frame). */}
          <section
            className="relative flex items-center py-10 md:min-h-[min(78vh,40rem)] md:py-12 lg:py-14"
            aria-label={t("nav.home")}
          >
            <Shell className="grid w-full items-center gap-8 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)] lg:gap-6 xl:gap-10">
              <div className="relative z-[2] flex flex-col gap-4 md:gap-5 lg:pr-4">
                <motion.div {...rise(0.04)}>
                  <LimenWordmark
                    size="xl"
                    className="text-riser max-w-full text-left text-[clamp(2.6rem,6vw,4.5rem)] leading-none tracking-[0.1em]"
                  />
                </motion.div>

                <motion.h1
                  {...rise(0.1)}
                  className="type-h1 m-0 max-w-[22ch] text-balance text-ice"
                >
                  {t("hero.headline")}
                </motion.h1>

                <motion.p
                  {...rise(0.16)}
                  className="type-body-l m-0 max-w-[40ch] text-pretty text-text-2"
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
                      glow
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
                        glow
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
                {...rise(0.14)}
                className="relative z-[1] flex items-center justify-center lg:justify-end"
              >
                <div
                  aria-hidden
                  className="pointer-events-none absolute left-1/2 top-1/2 h-[min(26rem,85%)] w-[min(26rem,95%)] -translate-x-1/2 -translate-y-1/2 lg:left-auto lg:right-[8%] lg:translate-x-0"
                  style={{
                    background: `
                      radial-gradient(
                        circle at 50% 48%,
                        color-mix(in oklab, var(--limen-action) 36%, transparent) 0%,
                        color-mix(in oklab, var(--limen-cyan) 14%, transparent) 42%,
                        transparent 72%
                      )
                    `,
                  }}
                />
                <motion.div
                  animate={{ y: [0, -5, 0] }}
                  transition={{
                    duration: 7.5,
                    repeat: Infinity,
                    ease: "easeInOut",
                  }}
                  className="relative z-[1]"
                >
                  <VoiceOrb
                    phase={voice.phase}
                    level={voice.level}
                    className="h-[clamp(16rem,42vh,28rem)] w-[clamp(16rem,42vh,28rem)]"
                  />
                </motion.div>
              </motion.div>
            </Shell>
          </section>

          {/* Problem — open editorial */}
          <section className="border-t border-[color-mix(in_oklab,var(--limen-ice)_14%,transparent)] py-12 md:py-16">
            <Shell>
              <motion.div
                {...reveal()}
                className="grid gap-4 md:grid-cols-[minmax(0,0.28fr)_minmax(0,0.72fr)] md:items-start md:gap-12"
              >
                <p className="type-eyebrow m-0 text-text-3">
                  {t("problem.eyebrow")}
                </p>
                <div>
                  <h2 className="type-h1 m-0 max-w-[26ch] text-balance text-ice">
                    {t("problem.title")}
                  </h2>
                  <p className="type-body-l mt-4 max-w-[52ch] text-pretty text-text-2">
                    {t("problem.body")}
                  </p>
                </div>
              </motion.div>
            </Shell>
          </section>

          {/* Pillars — feature cards with luminous icon wells */}
          <section className="border-t border-[color-mix(in_oklab,var(--limen-ice)_14%,transparent)] py-16 md:py-20">
            <Shell>
              <motion.div
                {...reveal()}
                className="mx-auto max-w-3xl text-center"
              >
                <p className="type-eyebrow m-0 text-text-3">
                  {t("pillars.eyebrow")}
                </p>
                <h2 className="type-h1 mt-3 text-balance text-ice">
                  {t("pillars.title")}
                </h2>
                <p className="type-body mt-4 text-pretty text-text-2">
                  {t("pillars.lead")}
                </p>
              </motion.div>

              <ul className="mt-12 m-0 grid list-none gap-4 p-0 sm:grid-cols-2 lg:mt-14 lg:grid-cols-4 lg:gap-5">
                {pillars.map(({ key, icon }, index) => (
                  <motion.li
                    key={key}
                    {...reveal(index * 0.06)}
                    className={cn(tileClass, "flex flex-col gap-5 p-6 md:p-7")}
                  >
                    <FeatureIcon icon={icon} size="lg" />
                    <div className="flex flex-col gap-2.5">
                      <h3 className="type-h3 m-0 text-ice">
                        {t(`pillars.${key}.name`)}
                      </h3>
                      <p className="type-body m-0 text-text-2">
                        {t(`pillars.${key}.body`)}
                      </p>
                    </div>
                  </motion.li>
                ))}
              </ul>
            </Shell>
          </section>

          {/* How it works — vertical clinical timeline + glass stage */}
          <section
            id="how-it-works"
            className="scroll-mt-28 border-t border-[color-mix(in_oklab,var(--limen-ice)_14%,transparent)] py-16 md:py-20"
          >
            <Shell>
              <motion.div
                {...reveal()}
                className="mx-auto max-w-3xl text-center lg:mx-0 lg:max-w-none lg:text-left"
              >
                <p className="type-eyebrow m-0 text-text-3">
                  {t("steps.eyebrow")}
                </p>
                <div className="mt-3 grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] lg:items-end lg:gap-12">
                  <h2 className="type-h1 m-0 text-balance text-ice">
                    {t("steps.title")}
                  </h2>
                  <p className="type-body m-0 text-pretty text-text-2 lg:pb-1">
                    {t("steps.lead")}
                  </p>
                </div>
              </motion.div>

              <div className="mt-12 grid gap-8 lg:mt-14 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:gap-12 lg:items-stretch">
                <ol className="relative m-0 flex list-none flex-col gap-0 p-0">
                  <span
                    aria-hidden
                    className="absolute bottom-4 left-[1.15rem] top-4 w-px md:left-[1.35rem]"
                    style={{
                      background: `linear-gradient(
                        to bottom,
                        color-mix(in oklab, var(--limen-action) 55%, transparent),
                        color-mix(in oklab, var(--limen-cyan) 35%, transparent),
                        color-mix(in oklab, var(--limen-teal) 20%, transparent)
                      )`,
                    }}
                  />
                  {steps.map((step, index) => (
                    <motion.li
                      key={step}
                      {...reveal(index * 0.07)}
                      className="relative flex gap-5 pb-10 last:pb-0 md:gap-6"
                    >
                      <span
                        className="relative z-[1] mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border md:h-11 md:w-11"
                        style={{
                          borderColor:
                            "color-mix(in oklab, var(--limen-action) 45%, transparent)",
                          background:
                            "color-mix(in oklab, var(--limen-bg-1) 80%, transparent)",
                          boxShadow:
                            "0 0 20px color-mix(in oklab, var(--limen-action) 18%, transparent)",
                        }}
                      >
                        <span className="type-label m-0 text-cyan">
                          {String(index + 1).padStart(2, "0")}
                        </span>
                      </span>
                      <div className="flex min-w-0 flex-col gap-2 pt-1">
                        <h3 className="type-h3 m-0 text-ice">
                          {t(`steps.${step}.title`)}
                        </h3>
                        <p className="type-body m-0 text-text-2">
                          {t(`steps.${step}.body`)}
                        </p>
                      </div>
                    </motion.li>
                  ))}
                </ol>

                <motion.div
                  {...reveal(0.12)}
                  className={cn(
                    tileClass,
                    "relative flex min-h-[18rem] flex-col items-center justify-center overflow-hidden p-8 md:min-h-[22rem]",
                    "hover:translate-y-0",
                  )}
                >
                  <div
                    aria-hidden
                    className="pointer-events-none absolute inset-0"
                    style={{
                      background: `
                        radial-gradient(
                          70% 60% at 50% 40%,
                          color-mix(in oklab, var(--limen-action) 18%, transparent),
                          transparent 70%
                        )
                      `,
                    }}
                  />
                  <VoiceOrb
                    phase={voice.phase}
                    level={voice.level}
                    className="relative z-[1] h-[clamp(11rem,28vh,16rem)] w-[clamp(11rem,28vh,16rem)]"
                  />
                </motion.div>
              </div>
            </Shell>
          </section>

          {/* Security */}
          <section
            id="security"
            className="scroll-mt-28 border-t border-[color-mix(in_oklab,var(--limen-ice)_14%,transparent)] py-16 md:py-20"
          >
            <Shell className="grid gap-12 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:gap-16 lg:items-start">
              <motion.div {...reveal()}>
                <p className="type-eyebrow m-0 text-text-3">
                  {t("security.eyebrow")}
                </p>
                <h2 className="type-h1 mt-3 max-w-[20ch] text-balance text-ice">
                  {t("security.title")}
                </h2>
                <p className="type-body-l mt-5 max-w-[42ch] text-pretty text-text-2">
                  {t("security.lead")}
                </p>
              </motion.div>

              <motion.dl
                {...reveal(0.06)}
                className={cn(
                  tileClass,
                  "m-0 flex flex-col divide-y divide-[color-mix(in_oklab,var(--limen-ice)_16%,transparent)] p-2 sm:p-3",
                  "hover:translate-y-0",
                )}
              >
                {guarantees.map(({ key, icon }, index) => (
                  <motion.div
                    key={key}
                    {...reveal(0.08 + index * 0.05)}
                    className="flex gap-5 px-4 py-5 first:pt-4 last:pb-4 sm:gap-6 sm:px-5 sm:py-6"
                  >
                    <FeatureIcon icon={icon} size="md" />
                    <div className="flex min-w-0 flex-col gap-2 pt-0.5">
                      <dt className="type-h3 m-0 text-ice">
                        {t(`security.${key}.title`)}
                      </dt>
                      <dd className="type-body m-0 text-text-2">
                        {t(`security.${key}.body`)}
                      </dd>
                    </div>
                  </motion.div>
                ))}
              </motion.dl>
            </Shell>
          </section>

          {/* Status — quiet band */}
          <section
            id="status"
            className="scroll-mt-28 border-t border-[color-mix(in_oklab,var(--limen-ice)_14%,transparent)] py-14 md:py-16"
          >
            <Shell>
              <motion.div
                {...reveal()}
                className="grid gap-4 md:grid-cols-[minmax(0,0.28fr)_minmax(0,0.72fr)] md:items-baseline md:gap-12"
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

          {/* Closing CTA — kept from prior polish */}
          <section className="pb-10 pt-6 md:pb-12 md:pt-8">
            <Shell>
              <motion.div
                {...reveal()}
                className={cn(
                  "relative flex flex-col gap-6 overflow-hidden rounded-lg p-8 md:flex-row md:items-center md:justify-between md:gap-12 md:p-10",
                  "border border-[color-mix(in_oklab,var(--limen-ice)_24%,transparent)]",
                  "bg-[var(--glass-surface-strong)] backdrop-blur-[20px]",
                )}
              >
                <div
                  aria-hidden
                  className="pointer-events-none absolute inset-0"
                  style={{
                    background: `radial-gradient(
                      68% 110% at 0% 50%,
                      color-mix(in oklab, var(--limen-action) 22%, transparent),
                      transparent 68%
                    )`,
                  }}
                />
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

          <footer className="border-t border-[color-mix(in_oklab,var(--limen-ice)_24%,transparent)] pb-10 pt-12 md:pb-12 md:pt-14">
            <Shell className="flex flex-col gap-12">
              <div className="grid gap-10 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1.6fr)_minmax(16rem,0.9fr)] lg:gap-12">
                <div className="flex flex-col gap-4">
                  <LimenLockup />
                  <p className="type-body-s m-0 max-w-[36ch] text-text-3">
                    {t("footer.tagline")}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-8 sm:grid-cols-3 sm:gap-10">
                  <FooterColumn title={t("footer.columns.product")}>
                    <FooterAnchor href="#how-it-works">
                      {t("footer.links.howItWorks")}
                    </FooterAnchor>
                    <FooterAnchor href="#security">
                      {t("footer.links.security")}
                    </FooterAnchor>
                    <FooterAnchor href="#status">
                      {t("footer.links.status")}
                    </FooterAnchor>
                  </FooterColumn>

                  <FooterColumn title={t("footer.columns.access")}>
                    {signedIn ? (
                      <FooterRoute to="/call">
                        {t("footer.links.enter")}
                      </FooterRoute>
                    ) : (
                      <>
                        <FooterRoute to="/login">
                          {t("footer.links.signIn")}
                        </FooterRoute>
                        <FooterRoute to="/register">
                          {t("footer.links.signUp")}
                        </FooterRoute>
                      </>
                    )}
                  </FooterColumn>

                  <FooterColumn title={t("footer.columns.legal")}>
                    <a
                      href="https://github.com/HCHAPS404/LIMEN/blob/main/LICENSE"
                      target="_blank"
                      rel="noreferrer"
                      className="type-body-s text-text-2 transition-colors hover:text-ice"
                    >
                      {t("footer.links.license")}
                    </a>
                  </FooterColumn>
                </div>

                <aside
                  className={cn(
                    "flex flex-col gap-3 rounded-lg p-5",
                    "border border-[color-mix(in_oklab,var(--limen-ice)_24%,transparent)]",
                    "bg-[var(--glass-surface)] backdrop-blur-[16px]",
                  )}
                >
                  <div className="flex items-center gap-2.5">
                    <LimenMark size={16} />
                    <div className="min-w-0">
                      <p className="type-body-s m-0 font-semibold text-ice">
                        {t("footer.note.title")}
                      </p>
                      <p className="type-body-s m-0 text-text-3">
                        {t("footer.note.handle")}
                      </p>
                    </div>
                  </div>
                  <p className="type-body-s m-0 text-text-2">
                    {t("footer.note.body")}
                  </p>
                </aside>
              </div>

              <div className="flex flex-col gap-4 border-t border-[color-mix(in_oklab,var(--limen-ice)_22%,transparent)] pt-6 sm:flex-row sm:items-center sm:justify-between">
                <p className="type-body-s m-0 flex items-center gap-2 text-text-3">
                  <LimenMark size={14} />
                  <span>{t("footer.copyright")}</span>
                  <span aria-hidden>·</span>
                  <span>{t("footer.license")}</span>
                </p>
                <div className="flex flex-wrap gap-4">
                  <FooterAnchor href="#how-it-works">
                    {t("nav.howItWorks")}
                  </FooterAnchor>
                  <FooterAnchor href="#security">{t("nav.security")}</FooterAnchor>
                </div>
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
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55, ease }}
        className={cn(
          SHELL,
          "glass-1 sheen-top flex h-14 items-center gap-2 rounded-full px-3 sm:gap-3 sm:px-5",
          "border border-[color-mix(in_oklab,var(--limen-ice)_16%,transparent)]",
          "shadow-[var(--shadow-panel)]",
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
          className="relative z-[1] hidden items-center gap-6 lg:flex"
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
      </motion.div>
    </header>
  );
}

function FooterColumn({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3.5">
      <p className="type-body-s m-0 font-semibold text-ice">{title}</p>
      <div className="flex flex-col gap-2.5">{children}</div>
    </div>
  );
}

function FooterAnchor({
  href,
  children,
}: {
  href: string;
  children: ReactNode;
}) {
  return (
    <a
      href={href}
      className="type-body-s text-text-2 transition-colors hover:text-ice"
    >
      {children}
    </a>
  );
}

function FooterRoute({
  to,
  children,
}: {
  to: string;
  children: ReactNode;
}) {
  return (
    <Link
      to={to}
      className="type-body-s text-text-2 transition-colors hover:text-ice"
    >
      {children}
    </Link>
  );
}
