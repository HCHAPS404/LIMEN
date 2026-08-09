import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";

import { callKeys, createCall, finishCall } from "../../api/calls";
import { describeError } from "../../api/client";
import { useVoicePersona, VOICE_PERSONAS } from "../../app/providers/VoicePersonaProvider";
import { createAudioSession, type AudioSession } from "../../audio/audio-session";
import { playCallEndCue, playCallStartCue } from "../../audio/call-cues";
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
  const [paused, setPaused] = useState(false);
  const pausedAtRef = useRef<number | null>(null);
  const pausedAccumMsRef = useRef(0);
  const queryClient = useQueryClient();
  const { personaId } = useVoicePersona();

  const phase = useCallStore((state) => state.phase);
  const micLevel = useCallStore((state) => state.micLevel);
  const startedAt = useCallStore((state) => state.startedAt);
  const callId = useCallStore((state) => state.callId);
  const transportStatus = useCallStore((state) => state.transportStatus);
  const reset = useCallStore((state) => state.reset);
  const setPhase = useCallStore((state) => state.setPhase);
  const setCallId = useCallStore((state) => state.setCallId);
  const setAssistantDisplayName = useCallStore(
    (state) => state.setAssistantDisplayName,
  );
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
      pausedAccumMsRef.current = 0;
      pausedAtRef.current = null;
      return;
    }
    const tick = () => {
      const pauseExtra =
        pausedAtRef.current != null ? Date.now() - pausedAtRef.current : 0;
      const activeMs =
        Date.now() - startedAt - pausedAccumMsRef.current - pauseExtra;
      setElapsed(Math.max(0, activeMs / 1000));
    };
    tick();
    const timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, [startedAt, paused]);

  // Server-driven hang-up (patient farewell / idle / max-duration): teardown only.
  // The WS path already persisted finish; client hang-up calls finishCall in end().
  useEffect(() => {
    if (phase !== "ENDED") return;
    setPaused(false);
    if (transportRef.current) {
      session.stop();
      transportRef.current.close();
      transportRef.current = null;
    }
    void queryClient.invalidateQueries({ queryKey: callKeys.all });
  }, [phase, session, queryClient]);

  const controls = useMemo(
    () => ({
      start: async () => {
        reset();
        setPaused(false);
        pausedAccumMsRef.current = 0;
        pausedAtRef.current = null;
        try {
          const created = await createCall({ voicePersona: personaId });
          setCallId(created.call_id);
          setAssistantDisplayName(
            VOICE_PERSONAS.find((p) => p.id === personaId)?.displayName ??
              personaId,
          );
          const transport = createCallTransport(session.playback);
          transportRef.current = transport;
          session.onBargeIn = () => {
            if (session.paused) return;
            transport.interrupt();
          };
          session.onUtterance = (payload) => {
            if (session.paused) return;
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
          transport.sendJson({
            type: "voice.select",
            persona_id: personaId,
          });
          transport.sendJson({ type: "voice.mic.requested" });
          transport.sendJson({ type: "voice.mic.granted" });
          void playCallStartCue();
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
      pause: () => {
        if (session.paused) return;
        session.pause();
        transportRef.current?.interrupt();
        pausedAtRef.current = Date.now();
        setPaused(true);
      },
      resume: () => {
        if (!session.paused) return;
        if (pausedAtRef.current != null) {
          pausedAccumMsRef.current += Date.now() - pausedAtRef.current;
          pausedAtRef.current = null;
        }
        session.resume();
        setPaused(false);
      },
      end: () => {
        const id = useCallStore.getState().callId;
        setPaused(false);
        pausedAtRef.current = null;
        // Hard-stop agent audio before teardown so hang-up never leaves TTS talking.
        session.playback.stop();
        transportRef.current?.interrupt();
        transportRef.current?.end();
        session.stop();
        setPhase("ENDED");
        void playCallEndCue();
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
        setPaused(false);
        transportRef.current?.close();
        transportRef.current = null;
        session.stop();
        reset();
      },
    }),
    [session, setPhase, reset, setCallId, setAssistantDisplayName, fail, queryClient, personaId],
  );

  const readWaveform = session.capture?.readWaveform ?? null;

  return {
    phase,
    micLevel,
    elapsed,
    paused,
    permission,
    callId,
    transportStatus,
    readWaveform,
    controls,
  };
}
