import type { CallPhase } from "../../api/types";

export type PhasePresentation = {
  label: string;
  /** Explains what the system is doing right now, in patient-safe language. */
  description: string;
  /** Token-driven accent for status text. Voice sphere colors come from voiceRole. */
  accent: string;
  animated: boolean;
};

export const phasePresentation: Record<CallPhase, PhasePresentation> = {
  IDLE: {
    label: "Idle",
    description: "No active session. Start a call to open the microphone.",
    accent: "var(--limen-text-3)",
    animated: false,
  },
  REQUESTING_MIC: {
    label: "Requesting microphone",
    description: "Waiting for browser microphone permission.",
    accent: "var(--limen-amber)",
    animated: true,
  },
  LISTENING: {
    label: "Listening",
    description: "You can speak. The field reacts to your voice.",
    accent: "var(--limen-voice-patient)",
    animated: true,
  },
  PROCESSING_STT: {
    label: "Transcribing",
    description: "Converting the last patient turn to text.",
    accent: "var(--limen-text-2)",
    animated: true,
  },
  THINKING: {
    label: "Reasoning",
    description: "Updating clinical state, retrieving evidence, evaluating safety.",
    accent: "var(--limen-violet)",
    animated: true,
  },
  SPEAKING: {
    label: "Speaking",
    description: "Playing the agent response. Speak to interrupt.",
    accent: "var(--limen-voice-agent)",
    animated: true,
  },
  INTERRUPTED: {
    label: "Interrupted",
    description: "Playback stopped because you started speaking.",
    accent: "var(--limen-voice-patient)",
    animated: false,
  },
  ERROR: {
    label: "Error",
    description: "The session cannot continue until the problem is resolved.",
    accent: "var(--limen-coral)",
    animated: false,
  },
  ENDED: {
    label: "Ended",
    description: "Session closed. The summary and trace are final.",
    accent: "var(--limen-text-2)",
    animated: false,
  },
};
