/** Realtime call transport: WebSocket ↔ call store.
 *  Does not invent clinical data — only applies typed backend events. */

import { callSocketUrl } from "../../api/calls";
import type { CallPhase, RealtimeEvent } from "../../api/types";
import type { AgentPlayback } from "../../audio/playback";
import { useCallStore } from "../../state/call-store";

export type TransportStatus =
  | "idle"
  | "connecting"
  | "open"
  | "closed"
  | "error";

export type CallTransport = {
  connect: (callId: string) => Promise<void>;
  sendAudio: (
    data: Blob | ArrayBuffer,
    meta?: { speechEndMonotonic?: number; turnSeq?: number },
  ) => void;
  sendJson: (payload: Record<string, unknown>) => void;
  interrupt: () => void;
  end: () => void;
  close: () => void;
  readonly status: TransportStatus;
  readonly pendingAudioTurnSeq: number | null;
};

function applyRealtimeEvent(event: RealtimeEvent, playback: AgentPlayback): void {
  const store = useCallStore.getState();

  switch (event.type) {
    case "call.state": {
      const next = event.payload.state as CallPhase;
      // Ignore premature LISTENING while TTS audio is still playing (echo guard).
      if (next === "LISTENING" && playback.playing) {
        (
          playback as AgentPlayback & { _deferListening?: boolean }
        )._deferListening = true;
        break;
      }
      store.applyServerPhase(next);
      const displayName = event.payload.voice_display_name;
      if (typeof displayName === "string" && displayName.trim()) {
        store.setAssistantDisplayName(displayName.trim());
      }
      break;
    }
    case "call.transcript":
      store.appendTurn(event.payload);
      break;
    case "call.clinical_state":
      store.setClinicalState(event.payload);
      break;
    case "call.safety":
      store.setSafety(
        event.payload.risk,
        event.payload.escalate,
        event.payload.reasons,
      );
      break;
    case "call.evidence":
      store.setEvidence(event.payload.chunks);
      break;
    case "call.metrics":
      store.setMetrics(event.payload);
      break;
    case "call.audio":
      // Metadata for the next binary frame (turn_seq / mime).
      (
        playback as AgentPlayback & {
          _pendingTurnSeq?: number;
        }
      )._pendingTurnSeq = Number(event.payload.turn_seq ?? NaN);
      break;
    case "call.error":
      store.fail({
        code: event.payload.code,
        message: event.payload.message,
      });
      break;
    case "call.ended":
      store.applyServerPhase("ENDED");
      // Farewell / idle / max-duration — manual hang-up plays its own cue.
      {
        const reason = String(event.payload.reason ?? event.payload.call_end_reason ?? "");
        if (
          reason === "patient_farewell" ||
          reason === "patient_wrapup" ||
          reason === "idle_prompt_timeout" ||
          reason === "max_duration" ||
          reason === "escalation"
        ) {
          void import("../../audio/call-cues").then(({ playCallEndCue }) => {
            void playCallEndCue();
          });
        }
      }
      break;
    default:
      break;
  }
}

export function createCallTransport(playback: AgentPlayback): CallTransport {
  let socket: WebSocket | null = null;
  let status: TransportStatus = "idle";
  let pendingAudioTurnSeq: number | null = null;

  const setStatus = (next: TransportStatus) => {
    status = next;
    useCallStore.getState().setTransportStatus(next);
  };

  playback.onPlaybackStarted = (meta) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    socket.send(
      JSON.stringify({
        type: "voice.playback.started",
        turn_seq: meta.turnSeq,
        agent_audio_started_monotonic: meta.agentAudioStartedMonotonic,
        agent_audio_received_monotonic: meta.agentAudioReceivedMonotonic,
      }),
    );
  };
  playback.onPlaybackCompleted = (meta) => {
    const deferred = (
      playback as AgentPlayback & { _deferListening?: boolean }
    )._deferListening;
    if (deferred) {
      (
        playback as AgentPlayback & { _deferListening?: boolean }
      )._deferListening = false;
    }
    const store = useCallStore.getState();
    // Local belt: if still SPEAKING when audio ends, open listening immediately.
    if (store.phase === "SPEAKING" || deferred) {
      store.applyServerPhase("LISTENING");
    }
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    socket.send(
      JSON.stringify({
        type: "voice.playback.completed",
        turn_seq: meta.turnSeq,
      }),
    );
  };

  return {
    get status() {
      return status;
    },
    get pendingAudioTurnSeq() {
      return pendingAudioTurnSeq;
    },

    connect(callId) {
      return new Promise((resolve, reject) => {
        if (socket) {
          socket.close();
          socket = null;
        }
        setStatus("connecting");
        const url = callSocketUrl(callId);
        const ws = new WebSocket(url);
        socket = ws;
        let settled = false;

        const settleOk = () => {
          if (settled) return;
          settled = true;
          window.clearTimeout(timeout);
          setStatus("open");
          resolve();
        };

        const settleErr = (message: string) => {
          if (settled) return;
          settled = true;
          window.clearTimeout(timeout);
          setStatus("error");
          try {
            ws.close();
          } catch {
            // ignore
          }
          if (socket === ws) socket = null;
          reject(new Error(message));
        };

        const timeout = window.setTimeout(() => {
          settleErr("Voice transport timed out while connecting.");
        }, 10_000);

        ws.binaryType = "arraybuffer";

        ws.onopen = () => {
          settleOk();
        };

        ws.onerror = () => {
          settleErr("Voice transport could not connect.");
        };

        ws.onclose = (event) => {
          if (!settled) {
            settleErr(
              `Voice transport closed before open (code ${event.code}).`,
            );
            return;
          }
          if (status !== "error") setStatus("closed");
          if (socket === ws) socket = null;
        };

        ws.onmessage = (message) => {
          if (typeof message.data !== "string") {
            const pending = (
              playback as AgentPlayback & { _pendingTurnSeq?: number }
            )._pendingTurnSeq;
            const turnSeq =
              typeof pending === "number" && Number.isFinite(pending)
                ? pending
                : null;
            pendingAudioTurnSeq = turnSeq;
            const blob = new Blob([message.data], { type: "audio/wav" });
            void playback.enqueue(blob, {
              turnSeq: turnSeq ?? undefined,
            });
            return;
          }
          try {
            const event = JSON.parse(message.data) as RealtimeEvent;
            applyRealtimeEvent(event, playback);
          } catch {
            // Ignore non-JSON text frames.
          }
        };
      });
    },

    sendAudio(data, meta) {
      if (!socket || socket.readyState !== WebSocket.OPEN) return;
      if (meta?.speechEndMonotonic != null) {
        socket.send(
          JSON.stringify({
            type: "voice.speech.ended",
            speech_end_monotonic: meta.speechEndMonotonic,
          }),
        );
      }
      if (data instanceof Blob) {
        void data.arrayBuffer().then((buffer) => {
          if (socket?.readyState === WebSocket.OPEN) socket.send(buffer);
        });
        return;
      }
      socket.send(data);
    },

    sendJson(payload) {
      if (!socket || socket.readyState !== WebSocket.OPEN) return;
      socket.send(JSON.stringify(payload));
    },

    interrupt() {
      this.sendJson({ type: "voice.interrupt" });
    },

    end() {
      this.sendJson({ type: "end" });
    },

    close() {
      if (socket) {
        socket.close();
        socket = null;
      }
      setStatus("closed");
    },
  };
}
