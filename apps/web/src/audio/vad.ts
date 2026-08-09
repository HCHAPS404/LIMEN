/** Endpointing defaults measured for pause-heavy Spanish (PHASE 6.3).
 *
 * LEVEL_POLL_MS = 60 → silenceFrames 28 ≈ 1680 ms silence before end-of-turn.
 * Prefer natural turn-taking over minimum latency.
 */
export const ENDPOINTING = {
  levelPollMs: 60,
  /** ~240 ms of speech before opening a segment. */
  speechFrames: 4,
  /** ~1680 ms silence to end (pause-heavy Spanish). */
  silenceFrames: 28,
  speechThreshold: 0.045,
  silenceThreshold: 0.02,
  minUtteranceMs: 320,
  maxUtteranceMs: 45_000,
  /** Sustained speech frames while SPEAKING before barge-in (~480 ms). */
  bargeInSpeechFrames: 8,
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
