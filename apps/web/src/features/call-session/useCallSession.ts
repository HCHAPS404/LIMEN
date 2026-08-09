import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";

import { callKeys, createCall, finishCall } from "../../api/calls";
import { describeError } from "../../api/client";
import { createAudioSession, type AudioSession } from "../../audio/audio-session";
import { queryMicrophonePermission } from "../../audio/recorder";
import { useCallStore } from "../../state/call-store";
import { createCallTransport, type CallTransport } from "./callTransport";

/** Owns microphone, call creation, WebSocket transport, and elapsed time.
 *  Clinical transcript/risk/evidence arrive only from realtime events. */
export function useCallSession() {
  const sessionRef = useRef<AudioSession | null>(null);
  const transportRef = useRef<CallTransport | null>(null);
  const [permission, setPermission] = useState<PermissionState | "unsupported">(
    "unsupported",
  );
  const [elapsed, setElapsed] = useState(0);
  const queryClient = useQueryClient();

  const phase = useCallStore((state) => state.phase);
  const micLevel = useCallStore((state) => state.micLevel);
  const startedAt = useCallStore((state) => state.startedAt);
  const callId = useCallStore((state) => state.callId);
  const transportStatus = useCallStore((state) => state.transportStatus);
  const reset = useCallStore((state) => state.reset);
  const setPhase = useCallStore((state) => state.setPhase);
  const setCallId = useCallStore((state) => state.setCallId);
  const fail = useCallStore((state) => state.fail);

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
      transportRef.current?.close();
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
      start: async () => {
        reset();
        try {
          const created = await createCall();
          setCallId(created.call_id);
          const transport = createCallTransport(session.playback);
          transportRef.current = transport;
          session.onBargeIn = () => {
            transport.interrupt();
          };
          session.onUtterance = (payload) => {
            const current = useCallStore.getState();
            if (
              current.phase !== "LISTENING" &&
              current.phase !== "INTERRUPTED"
            ) {
              return;
            }
            transport.sendAudio(payload.blob, {
              speechEndMonotonic: payload.speechEndMonotonic,
            });
          };
          await session.start();
          if (useCallStore.getState().phase === "ERROR") {
            transport.close();
            transportRef.current = null;
            return;
          }
          await transport.connect(created.call_id);
          transport.sendJson({ type: "voice.mic.requested" });
          transport.sendJson({ type: "voice.mic.granted" });
          void queryClient.invalidateQueries({ queryKey: callKeys.all });
        } catch (error) {
          session.stop();
          transportRef.current?.close();
          transportRef.current = null;
          fail({
            code: "transport_failed",
            message: describeError(error),
          });
        }
      },
      end: () => {
        const id = useCallStore.getState().callId;
        transportRef.current?.end();
        session.stop();
        setPhase("ENDED");
        transportRef.current?.close();
        transportRef.current = null;
        if (id) {
          void finishCall(id)
            .catch(() => undefined)
            .finally(() => {
              void queryClient.invalidateQueries({ queryKey: callKeys.all });
            });
        }
      },
      discard: () => {
        transportRef.current?.close();
        transportRef.current = null;
        session.stop();
        reset();
      },
    }),
    [session, setPhase, reset, setCallId, fail, queryClient],
  );

  const readWaveform = session.capture?.readWaveform ?? null;

  return {
    phase,
    micLevel,
    elapsed,
    permission,
    callId,
    transportStatus,
    readWaveform,
    controls,
  };
}
