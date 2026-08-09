/** Short UI cue tones for call start / hang-up (Web Audio, no asset files). */

let sharedCtx: AudioContext | null = null;

function audioContext(): AudioContext | null {
  if (typeof window === "undefined") return null;
  const Ctx =
    window.AudioContext ||
    (window as unknown as { webkitAudioContext?: typeof AudioContext })
      .webkitAudioContext;
  if (!Ctx) return null;
  if (!sharedCtx || sharedCtx.state === "closed") {
    sharedCtx = new Ctx();
  }
  return sharedCtx;
}

async function resume(ctx: AudioContext): Promise<void> {
  if (ctx.state === "suspended") {
    try {
      await ctx.resume();
    } catch {
      // Autoplay policies may block; fail silently.
    }
  }
}

function tone(
  ctx: AudioContext,
  {
    frequency,
    start,
    duration,
    type = "sine",
    gain = 0.08,
  }: {
    frequency: number;
    start: number;
    duration: number;
    type?: OscillatorType;
    gain?: number;
  },
): void {
  if (typeof ctx.createOscillator !== "function" || typeof ctx.createGain !== "function") {
    return;
  }
  const osc = ctx.createOscillator();
  const amp = ctx.createGain();
  osc.type = type;
  osc.frequency.value = frequency;
  amp.gain.setValueAtTime(0.0001, start);
  amp.gain.exponentialRampToValueAtTime(gain, start + 0.02);
  amp.gain.exponentialRampToValueAtTime(0.0001, start + duration);
  osc.connect(amp);
  amp.connect(ctx.destination);
  osc.start(start);
  osc.stop(start + duration + 0.02);
}

/** Soft ascending chirp when the call becomes live. */
export async function playCallStartCue(): Promise<void> {
  try {
    const ctx = audioContext();
    if (!ctx) return;
    await resume(ctx);
    const t0 = ctx.currentTime + 0.02;
    tone(ctx, { frequency: 523.25, start: t0, duration: 0.09, gain: 0.07 });
    tone(ctx, { frequency: 659.25, start: t0 + 0.08, duration: 0.11, gain: 0.06 });
  } catch {
    // Tests / restricted AudioContext — never block the call path.
  }
}

/** Soft descending chirp when the call ends. */
export async function playCallEndCue(): Promise<void> {
  try {
    const ctx = audioContext();
    if (!ctx) return;
    await resume(ctx);
    const t0 = ctx.currentTime + 0.02;
    tone(ctx, { frequency: 659.25, start: t0, duration: 0.1, gain: 0.06 });
    tone(ctx, { frequency: 440.0, start: t0 + 0.1, duration: 0.14, gain: 0.05 });
  } catch {
    // Tests / restricted AudioContext — never block hang-up.
  }
}
