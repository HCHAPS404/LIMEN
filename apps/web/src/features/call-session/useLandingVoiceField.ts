import { useEffect, useRef, useState } from "react";

import type { CallPhase } from "../../api/types";
import {
  openMicrophone,
  type MicrophoneCapture,
} from "../../audio/recorder";

const LEVEL_POLL_MS = 50;
/** Raw RMS above this counts as visitor speech on the landing field. */
const SPEECH_FLOOR = 0.012;

/**
 * Landing-only voice field. Opens the real microphone when allowed and drives
 * a single color change: idle → patient blue while someone speaks.
 * Agent orange and processing states belong to the call workspace only —
 * this surface never demos AI turns.
 */
export function useLandingVoiceField() {
  const [level, setLevel] = useState(0);
  const [phase, setPhase] = useState<CallPhase>("IDLE");
  const captureRef = useRef<MicrophoneCapture | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setInterval> | null = null;

    void (async () => {
      try {
        const capture = await openMicrophone();
        if (cancelled) {
          capture.stop();
          return;
        }
        captureRef.current = capture;
        timer = setInterval(() => {
          const next = capture.readLevel();
          setLevel(next);
          setPhase(next > SPEECH_FLOOR ? "LISTENING" : "IDLE");
        }, LEVEL_POLL_MS);
      } catch {
        // Mic blocked: stay idle. No synthetic agent/patient demo on landing.
        if (!cancelled) {
          setLevel(0);
          setPhase("IDLE");
        }
      }
    })();

    return () => {
      cancelled = true;
      if (timer !== null) clearInterval(timer);
      captureRef.current?.stop();
      captureRef.current = null;
    };
  }, []);

  return { level, phase };
}
