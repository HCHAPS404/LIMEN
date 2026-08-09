import { useEffect, useRef, useState } from "react";

import type { CallPhase } from "../../api/types";
import {
  openMicrophone,
  type MicrophoneCapture,
} from "../../audio/recorder";

const LEVEL_POLL_MS = 50;
const SPEECH_FLOOR = 0.012;

/**
 * Landing-only voice field. Mic opens only after an explicit enable gesture
 * (browsers require a user gesture for capture; auto-open on mount is hostile).
 */
export function useLandingVoiceField() {
  const [level, setLevel] = useState(0);
  const [phase, setPhase] = useState<CallPhase>("IDLE");
  const [enabled, setEnabled] = useState(false);
  const captureRef = useRef<MicrophoneCapture | null>(null);

  useEffect(() => {
    if (!enabled) {
      captureRef.current?.stop();
      captureRef.current = null;
      setLevel(0);
      setPhase("IDLE");
      return;
    }

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
        if (!cancelled) {
          setLevel(0);
          setPhase("IDLE");
          setEnabled(false);
        }
      }
    })();

    return () => {
      cancelled = true;
      if (timer !== null) clearInterval(timer);
      captureRef.current?.stop();
      captureRef.current = null;
    };
  }, [enabled]);

  return {
    level,
    phase,
    enabled,
    enable: () => setEnabled(true),
    disable: () => setEnabled(false),
  };
}
