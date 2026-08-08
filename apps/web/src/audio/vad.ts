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
  reset: () => void;
};

export function createVad(options: VadOptions = {}): VoiceActivityDetector {
  const speechThreshold = options.speechThreshold ?? 0.045;
  const silenceThreshold = options.silenceThreshold ?? 0.02;
  const speechFrames = options.speechFrames ?? 3;
  const silenceFrames = options.silenceFrames ?? 12;

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
    reset() {
      state = "silence";
      speechRun = 0;
      silenceRun = 0;
    },
  };
}
