/**
 * Single light field for the authenticated shell.
 * Sits behind header + rail + workspace so chrome stays translucent over one continuous wash.
 * Chrome must not paint competing radials — those clip into hard seams.
 */
export function WorkspaceAtmosphere() {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 z-0 overflow-hidden"
    >
      <div
        className="absolute inset-0"
        style={{
          background: `
            radial-gradient(
              95% 75% at 8% -12%,
              color-mix(in oklab, var(--limen-beam) var(--atmo-beam), transparent) 0%,
              color-mix(in oklab, var(--limen-beam) 9%, transparent) 38%,
              transparent 78%
            ),
            radial-gradient(
              75% 60% at 92% 4%,
              color-mix(in oklab, var(--limen-cyan) var(--atmo-cyan), transparent) 0%,
              color-mix(in oklab, var(--limen-cyan) 6%, transparent) 40%,
              transparent 76%
            ),
            radial-gradient(
              58% 48% at 48% 36%,
              color-mix(in oklab, var(--limen-action) 11%, transparent) 0%,
              color-mix(in oklab, var(--limen-teal) 5%, transparent) 40%,
              transparent 74%
            ),
            radial-gradient(
              85% 58% at 50% 110%,
              color-mix(in oklab, var(--limen-teal) var(--atmo-teal), transparent) 0%,
              color-mix(in oklab, var(--limen-teal) 6%, transparent) 46%,
              transparent 82%
            ),
            linear-gradient(
              168deg,
              var(--limen-bg-1) 0%,
              var(--limen-bg-0) 44%,
              var(--limen-bg-0) 100%
            )
          `,
        }}
      />
    </div>
  );
}
