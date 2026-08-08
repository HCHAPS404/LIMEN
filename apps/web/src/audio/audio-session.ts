/** Binds microphone capture, voice activity detection, and agent playback to the
 *  call store. The transport that carries audio to STT and returns synthesized
 *  speech lands with the voice backend; this module owns only the browser side. */

import { useCallStore } from "../state/call-store";
import { createAgentPlayback, type AgentPlayback } from "./playback";
import {
  MIC_ERROR_COPY,
  MicrophoneError,
  openMicrophone,
  type MicrophoneCapture,
} from "./recorder";
import { createVad, type VoiceActivityDetector } from "./vad";

export type AudioSession = {
  start: () => Promise<void>;
  stop: () => void;
  readonly capture: MicrophoneCapture | null;
  readonly playback: AgentPlayback;
};

const LEVEL_POLL_MS = 60;

export function createAudioSession(): AudioSession {
  let capture: MicrophoneCapture | null = null;
  let timer: ReturnType<typeof setInterval> | null = null;
  let vad: VoiceActivityDetector | null = null;
  const playback = createAgentPlayback();

  const store = () => useCallStore.getState();

  const poll = () => {
    if (!capture || !vad) return;
    const level = capture.readLevel();
    store().setMicLevel(level);

    const speaking = vad.push(level) === "speech";
    const previous = store().patientSpeaking;
    if (speaking === previous) return;

    store().setPatientSpeaking(speaking);

    // Barge-in: patient speech always wins over agent playback.
    if (speaking && store().phase === "SPEAKING") {
      playback.stop();
      store().markLastAgentTurnInterrupted();
      store().setPhase("INTERRUPTED");
      store().setPhase("LISTENING");
    }
  };

  return {
    async start() {
      if (capture) return;
      store().setPhase("REQUESTING_MIC");
      try {
        capture = await openMicrophone();
      } catch (error) {
        const reason =
          error instanceof MicrophoneError ? error.reason : "UNKNOWN";
        store().fail({ code: reason, message: MIC_ERROR_COPY[reason] });
        return;
      }
      vad = createVad();
      store().setPhase("LISTENING");
      timer = setInterval(poll, LEVEL_POLL_MS);
    },

    stop() {
      if (timer !== null) {
        clearInterval(timer);
        timer = null;
      }
      playback.stop();
      capture?.stop();
      capture = null;
      vad = null;
      store().setMicLevel(0);
      store().setPatientSpeaking(false);
    },

    get capture() {
      return capture;
    },

    playback,
  };
}
