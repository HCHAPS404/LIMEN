/** Binds microphone capture, VAD, PCM utterance recording, and agent playback.
 *  Utterance WAV blobs go to the call transport for STT — never transcribed here. */

import { useCallStore } from "../state/call-store";
import { createAgentPlayback, type AgentPlayback } from "./playback";
import {
  MIC_ERROR_COPY,
  MicrophoneError,
  openMicrophone,
  type MicrophoneCapture,
} from "./recorder";
import { createVad, ENDPOINTING, type VoiceActivityDetector } from "./vad";
import { floatChunksToWav } from "./wav";

export type UtterancePayload = {
  blob: Blob;
  speechEndMonotonic: number;
};

export type AudioSession = {
  start: () => Promise<void>;
  stop: () => void;
  onUtterance: ((payload: UtterancePayload) => void) | null;
  onBargeIn: (() => void) | null;
  readonly capture: MicrophoneCapture | null;
  readonly playback: AgentPlayback;
  /** Actual getUserMedia constraint support when the browser exposes it. */
  readonly audioConstraintsApplied: Record<string, boolean | string> | null;
};

const LEVEL_POLL_MS = ENDPOINTING.levelPollMs;
const MAX_UTTERANCE_MS = ENDPOINTING.maxUtteranceMs;
const MIN_UTTERANCE_MS = ENDPOINTING.minUtteranceMs;
const BARGE_IN_SPEECH_FRAMES = ENDPOINTING.bargeInSpeechFrames;

export function createAudioSession(): AudioSession {
  let capture: MicrophoneCapture | null = null;
  let timer: ReturnType<typeof setInterval> | null = null;
  let vad: VoiceActivityDetector | null = null;
  let recording = false;
  let pcmChunks: Float32Array[] = [];
  let utteranceStartedAt = 0;
  let processor: ScriptProcessorNode | null = null;
  let micSource: MediaStreamAudioSourceNode | null = null;
  const playback = createAgentPlayback();
  let onUtterance: ((payload: UtterancePayload) => void) | null = null;
  let onBargeIn: (() => void) | null = null;
  let audioConstraintsApplied: Record<string, boolean | string> | null = null;
  let bargeSpeechRun = 0;

  const store = () => useCallStore.getState();

  const startRecorder = () => {
    if (!capture || recording) return;
    pcmChunks = [];
    utteranceStartedAt = performance.now();
    recording = true;
  };

  const stopRecorder = () => {
    if (!recording) return;
    recording = false;
    const duration = performance.now() - utteranceStartedAt;
    const speechEndMonotonic = performance.now() / 1000;
    if (duration < MIN_UTTERANCE_MS || pcmChunks.length === 0 || !capture) {
      pcmChunks = [];
      return;
    }
    const blob = floatChunksToWav(pcmChunks, capture.context.sampleRate);
    pcmChunks = [];
    if (blob.size > 44) {
      onUtterance?.({ blob, speechEndMonotonic });
    }
  };

  const poll = () => {
    if (!capture || !vad) return;
    const level = capture.readLevel();
    store().setMicLevel(level);

    const speaking = vad.push(level) === "speech";
    const previous = store().patientSpeaking;
    const phase = store().phase;

    // While assistant is speaking, require sustained speech before barge-in
    // (echo / brief spikes must not stop playback).
    if (phase === "SPEAKING") {
      if (speaking) {
        bargeSpeechRun += 1;
      } else {
        bargeSpeechRun = 0;
      }
      if (bargeSpeechRun >= BARGE_IN_SPEECH_FRAMES) {
        playback.stop();
        store().markLastAgentTurnInterrupted();
        store().setPhase("INTERRUPTED");
        onBargeIn?.();
        store().setPhase("LISTENING");
        store().setPatientSpeaking(true);
        bargeSpeechRun = 0;
        startRecorder();
      }
      return;
    }

    bargeSpeechRun = 0;

    if (speaking === previous) {
      // Still track recording end even if patientSpeaking flag unchanged.
      if (!speaking && recording && phase === "LISTENING") {
        stopRecorder();
      }
      return;
    }

    store().setPatientSpeaking(speaking);

    if (speaking && store().phase === "LISTENING") {
      startRecorder();
    } else if (!speaking && recording) {
      stopRecorder();
    }
  };

  return {
    get onUtterance() {
      return onUtterance;
    },
    set onUtterance(handler) {
      onUtterance = handler;
    },
    get onBargeIn() {
      return onBargeIn;
    },
    set onBargeIn(handler) {
      onBargeIn = handler;
    },
    get capture() {
      return capture;
    },
    get playback() {
      return playback;
    },
    get audioConstraintsApplied() {
      return audioConstraintsApplied;
    },
    async start() {
      store().setPhase("REQUESTING_MIC");
      try {
        capture = await openMicrophone();
        audioConstraintsApplied = readAppliedConstraints(capture.stream);
        vad = createVad({
          speechThreshold: ENDPOINTING.speechThreshold,
          silenceThreshold: ENDPOINTING.silenceThreshold,
          speechFrames: ENDPOINTING.speechFrames,
          silenceFrames: ENDPOINTING.silenceFrames,
        });
        const ctx = capture.context;
        micSource = ctx.createMediaStreamSource(capture.stream);
        processor = ctx.createScriptProcessor(4096, 1, 1);
        const silent = ctx.createGain();
        silent.gain.value = 0;
        processor.onaudioprocess = (event) => {
          if (!recording) return;
          const input = event.inputBuffer.getChannelData(0);
          pcmChunks.push(new Float32Array(input));
          if (performance.now() - utteranceStartedAt > MAX_UTTERANCE_MS) {
            stopRecorder();
          }
        };
        micSource.connect(processor);
        processor.connect(silent);
        silent.connect(ctx.destination);

        store().setPhase("LISTENING");
        timer = setInterval(poll, LEVEL_POLL_MS);
      } catch (error) {
        const message =
          error instanceof MicrophoneError
            ? error.message
            : MIC_ERROR_COPY.UNKNOWN;
        store().fail({
          code:
            error instanceof MicrophoneError ? error.reason : "MIC_UNKNOWN",
          message,
        });
      }
    },
    stop() {
      if (timer) clearInterval(timer);
      timer = null;
      if (recording) stopRecorder();
      try {
        processor?.disconnect();
        micSource?.disconnect();
      } catch {
        /* ignore */
      }
      processor = null;
      micSource = null;
      vad?.reset();
      vad = null;
      capture?.stop();
      capture = null;
      audioConstraintsApplied = null;
      bargeSpeechRun = 0;
      store().setMicLevel(0);
      store().setPatientSpeaking(false);
    },
  };
}

function readAppliedConstraints(
  stream: MediaStream,
): Record<string, boolean | string> | null {
  const track = stream.getAudioTracks()[0];
  if (!track || typeof track.getSettings !== "function") return null;
  const settings = track.getSettings();
  const out: Record<string, boolean | string> = {};
  for (const key of [
    "echoCancellation",
    "noiseSuppression",
    "autoGainControl",
  ] as const) {
    const value = settings[key];
    if (typeof value === "boolean" || typeof value === "string") {
      out[key] = value;
    }
  }
  return Object.keys(out).length ? out : null;
}
