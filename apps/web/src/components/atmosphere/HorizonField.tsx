import { motion } from "framer-motion";

const ease = [0.22, 0.61, 0.36, 1] as const;

/**
 * Entry-surface atmosphere, shared by the landing hero and the auth screens.
 * Uses the same canvas tokens as the workspace (`--limen-bg-0` / beam / cyan /
 * teal) and the same `--atmo-*` mix ratios, so light and dark stay balanced.
 */
export function HorizonField({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={className ?? "absolute inset-0 overflow-hidden"}
    >
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1.2, ease }}
        className="absolute inset-0"
        style={{
          background: `
            radial-gradient(
              110% 70% at 50% -15%,
              color-mix(in oklab, var(--limen-beam) var(--atmo-beam), transparent),
              transparent 58%
            ),
            radial-gradient(
              60% 40% at 90% 20%,
              color-mix(in oklab, var(--limen-cyan) var(--atmo-cyan), transparent),
              transparent 55%
            ),
            radial-gradient(
              70% 50% at 50% 110%,
              color-mix(in oklab, var(--limen-teal) var(--atmo-teal), transparent),
              transparent 60%
            )
          `,
        }}
      />

      <div
        className="absolute inset-0 opacity-[0.14]"
        style={{
          backgroundImage: `radial-gradient(
            circle at center,
            color-mix(in oklab, var(--limen-ice) 30%, transparent) 0.55px,
            transparent 0.65px
          )`,
          backgroundSize: "28px 28px",
          maskImage:
            "radial-gradient(ellipse 65% 55% at 50% 38%, black 15%, transparent 72%)",
          WebkitMaskImage:
            "radial-gradient(ellipse 65% 55% at 50% 38%, black 15%, transparent 72%)",
        }}
      />

      <motion.div
        initial={{ opacity: 0, scaleY: 0.72 }}
        animate={{ opacity: 1, scaleY: 1 }}
        transition={{ duration: 1.4, delay: 0.15, ease }}
        className="absolute bottom-0 left-1/2 h-[52%] w-[min(48rem,88vw)] origin-bottom -translate-x-1/2"
        style={{
          background: `linear-gradient(
            to top,
            color-mix(in oklab, var(--limen-beam) var(--atmo-beam), transparent),
            transparent 78%
          )`,
          maskImage:
            "linear-gradient(to right, transparent, black 22%, black 78%, transparent)",
          WebkitMaskImage:
            "linear-gradient(to right, transparent, black 22%, black 78%, transparent)",
        }}
      />
    </div>
  );
}
