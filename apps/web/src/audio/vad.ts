/** Endpointing defaults measured for pause-heavy / talkative Spanish.
 *
 * LEVEL_POLL_MS = 60 → silenceFrames 32 ≈ 1920 ms silence before end-of-turn.
 * Prefer letting storytellers finish a thought over snappy cutoffs.
 */
export const ENDPOINTING = {
  levelPollMs: 60,
  /** ~120 ms of speech before opening a segment (keep leading "Hola"). */
  speechFrames: 2,
  /** ~1920 ms silence to end — talkative patients pause mid-story. */
  silenceFrames: 32,
  speechThreshold: 0.040,
  silenceThreshold: 0.018,
  minUtteranceMs: 280,
  /** Allow longer patient narratives without hard cut. */
  maxUtteranceMs: 90_000,
  /** Sustained energy while SPEAKING before barge-in (~540 ms). */
  bargeInSpeechFrames: 9,
  /** Slightly above speechThreshold — intentional speech, not TTS room bleed. */
  bargeInSpeechThreshold: 0.055,
  /** Ignore mic speech briefly after TTS ends (acoustic echo tail). */
  postPlaybackHoldoffMs: 550,
  /** After barge-in, wait for silence then new speech before recording. */
  postBargeSilenceFrames: 4,
  /** Keep ~360 ms of audio before VAD opens so leading syllables are not cut. */
  preRollMs: 360,
} as const;

/** Energy-threshold voice activity detection.
 *  Deterministic and dependency-free: it drives barge-in without needing STT. */

export type VadOptions = {
  /** RMS level above which the frame counts as speech. */
  speechThreshold?: number;
  /** RMS level below which the frame counts as silence (hysteresis). */
  silenceThreshold?: number;
  /** Consecutive speech frames required to open a segment. */
  speechFrames?: number;
  /** Consecutive silence frames required to close a segment. */
  silenceFrames?: number;
};

export type VadState = "silence" | "speech";

export type VoiceActivityDetector = {
  /** Feed one RMS level; returns the state after the frame. */
  push: (level: number) => VadState;
  readonly state: VadState;
  /** Consecutive speech frames in the current run (for barge-in gating). */
  readonly speechRun: number;
  reset: () => void;
};

export function createVad(options: VadOptions = {}): VoiceActivityDetector {
  const speechThreshold = options.speechThreshold ?? ENDPOINTING.speechThreshold;
  const silenceThreshold = options.silenceThreshold ?? ENDPOINTING.silenceThreshold;
  const speechFrames = options.speechFrames ?? ENDPOINTING.speechFrames;
  const silenceFrames = options.silenceFrames ?? ENDPOINTING.silenceFrames;

  let state: VadState = "silence";
  let speechRun = 0;
  let silenceRun = 0;

  return {
    push(level) {
      if (level >= speechThreshold) {
        speechRun += 1;
        silenceRun = 0;
      } else if (level <= silenceThreshold) {
        silenceRun += 1;
        speechRun = 0;
      }

      if (state === "silence" && speechRun >= speechFrames) {
        state = "speech";
        silenceRun = 0;
      } else if (state === "speech" && silenceRun >= silenceFrames) {
        state = "silence";
        speechRun = 0;
      }

      return state;
    },
    get state() {
      return state;
    },
    get speechRun() {
      return speechRun;
    },
    reset() {
      state = "silence";
      speechRun = 0;
      silenceRun = 0;
    },
  };
}
