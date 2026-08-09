import { useEffect, useRef, useState } from "react";

import type { CallPhase } from "../../api/types";
import {
  openMicrophone,
  type MicrophoneCapture,
} from "../../audio/recorder";

const LEVEL_POLL_MS = 50;
const SPEECH_FLOOR = 0.012;

/**
 * Landing voice field: the orb always animates (ambient).
 * Mic capture is attempted quietly for reactive motion; failure stays ambient
 * with no “enable microphone” CTA (browsers may still deny without a gesture).
 */
export function useLandingVoiceField() {
  const [level, setLevel] = useState(0.04);
  const [phase, setPhase] = useState<CallPhase>("IDLE");
  const captureRef = useRef<MicrophoneCapture | null>(null);
  const ambientRef = useRef(0);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setInterval> | null = null;
    let micReady = false;

    const startAmbient = () => {
      timer = setInterval(() => {
        if (cancelled) return;
        if (micReady && captureRef.current) {
          const next = captureRef.current.readLevel();
          setLevel(next);
          setPhase(next > SPEECH_FLOOR ? "LISTENING" : "IDLE");
          return;
        }
        ambientRef.current += 0.045;
        const wave =
          0.035 +
          0.025 * Math.sin(ambientRef.current) +
          0.012 * Math.sin(ambientRef.current * 0.37);
        setLevel(wave);
        setPhase("IDLE");
      }, LEVEL_POLL_MS);
    };

    startAmbient();

    void (async () => {
      try {
        const capture = await openMicrophone();
        if (cancelled) {
          capture.stop();
          return;
        }
        captureRef.current = capture;
        micReady = true;
      } catch {
        // Keep ambient animation — no CTA, no error chrome on the landing hero.
        micReady = false;
      }
    })();

    return () => {
      cancelled = true;
      if (timer !== null) clearInterval(timer);
      captureRef.current?.stop();
      captureRef.current = null;
    };
  }, []);

  return {
    level,
    phase,
    enabled: true,
    enable: () => undefined,
    disable: () => undefined,
  };
}
