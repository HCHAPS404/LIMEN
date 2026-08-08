import { useEffect, useMemo, useRef, useState } from "react";

import { createAudioSession, type AudioSession } from "../../audio/audio-session";
import { queryMicrophonePermission } from "../../audio/recorder";
import { useCallStore } from "../../state/call-store";

/** Owns the browser side of a voice session: microphone lifecycle, level
 *  polling, barge-in, and elapsed time. Turn processing arrives over the
 *  realtime channel once the voice backend exists, so nothing here fabricates
 *  transcripts, risk, or evidence. */
export function useCallSession() {
  const sessionRef = useRef<AudioSession | null>(null);
  const [permission, setPermission] = useState<PermissionState | "unsupported">(
    "unsupported",
  );
  const [elapsed, setElapsed] = useState(0);

  const phase = useCallStore((state) => state.phase);
  const micLevel = useCallStore((state) => state.micLevel);
  const startedAt = useCallStore((state) => state.startedAt);
  const reset = useCallStore((state) => state.reset);
  const setPhase = useCallStore((state) => state.setPhase);

  if (sessionRef.current === null) {
    sessionRef.current = createAudioSession();
  }
  const session = sessionRef.current;

  useEffect(() => {
    let cancelled = false;
    void queryMicrophonePermission().then((state) => {
      if (!cancelled) setPermission(state);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    return () => {
      session.stop();
      session.playback.dispose();
    };
  }, [session]);

  useEffect(() => {
    if (startedAt === null) {
      setElapsed(0);
      return;
    }
    const tick = () => setElapsed((Date.now() - startedAt) / 1000);
    tick();
    const timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, [startedAt]);

  const controls = useMemo(
    () => ({
      start: () => session.start(),
      end: () => {
        session.stop();
        setPhase("ENDED");
      },
      discard: () => {
        session.stop();
        reset();
      },
    }),
    [session, setPhase, reset],
  );

  const readWaveform = session.capture?.readWaveform ?? null;

  return { phase, micLevel, elapsed, permission, readWaveform, controls };
}
