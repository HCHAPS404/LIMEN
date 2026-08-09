import type { CallPhase } from "../../api/types";

/** Who currently "owns" the voice sphere color. Distinct from clinical risk. */
export type VoiceRole = "idle" | "patient" | "agent" | "processing";

/**
 * Maps call phase to speaker color role.
 * - patient: microphone open / patient turn (blue → white)
 * - agent: TTS playback (orange → white)
 * - processing: STT / reasoning (neutral ice)
 * - idle: resting dark mesh
 */
export function voiceRoleFromPhase(phase: CallPhase): VoiceRole {
  switch (phase) {
    case "LISTENING":
    case "INTERRUPTED":
    case "REQUESTING_MIC":
      return "patient";
    case "SPEAKING":
      return "agent";
    case "PROCESSING_STT":
    case "THINKING":
      return "processing";
    default:
      return "idle";
  }
}

/**
 * Effective animation energy for the voice sphere.
 *
 * Browser RMS for quiet speech sits around 0.02–0.15, so a raw pass-through
 * barely moves the mesh. Patient energy is gained and soft-kneed so soft speech
 * still deforms the field without clipping on a loud turn. Agent and processing
 * keep synthetic pulses — there is no mic level for those phases.
 */
export function voiceEnergy(
  role: VoiceRole,
  micLevel: number,
  timeMs: number,
): number {
  const mic = Math.min(1, Math.max(0, micLevel));
  if (role === "patient") {
    // Slightly hotter gain for soft speech; still soft-caps so loud peaks
    // do not push the mesh past the canvas edge.
    return Math.min(0.78, Math.pow(mic * 4.8, 0.65));
  }
  if (role === "agent") {
    return 0.36 + 0.28 * (0.5 + 0.5 * Math.sin(timeMs * 0.0048));
  }
  if (role === "processing") {
    return 0.2 + 0.14 * (0.5 + 0.5 * Math.sin(timeMs * 0.0034));
  }
  return 0.05 + 0.03 * (0.5 + 0.5 * Math.sin(timeMs * 0.0016));
}
