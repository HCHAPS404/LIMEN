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
  /** Temporarily stop listening/playback without tearing down the call. */
  pause: () => void;
  resume: () => void;
  readonly paused: boolean;
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
const BARGE_IN_LEVEL = ENDPOINTING.bargeInSpeechThreshold;
const POST_PLAYBACK_HOLDOFF_MS = ENDPOINTING.postPlaybackHoldoffMs;
const POST_BARGE_SILENCE_FRAMES = ENDPOINTING.postBargeSilenceFrames;

type BargeArm = "idle" | "wait_silence" | "armed";

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
  let ignoreSpeechUntil = 0;
  let bargeArm: BargeArm = "idle";
  let postBargeSilenceRun = 0;
  let unsubPlayback: (() => void) | null = null;
  /** Ring buffer of recent mic PCM so VAD open does not clip "Hola…". */
  let preRoll: Float32Array[] = [];
  let preRollSamples = 0;
  let paused = false;

  const store = () => useCallStore.getState();

  const setMicTracksEnabled = (enabled: boolean) => {
    const stream = capture?.stream;
    if (!stream) return;
    for (const track of stream.getAudioTracks()) {
      track.enabled = enabled;
    }
  };

  const discardRecorder = () => {
    recording = false;
    pcmChunks = [];
  };

  const pushPreRoll = (chunk: Float32Array) => {
    if (!capture) return;
    const maxSamples = Math.ceil(
      (capture.context.sampleRate * ENDPOINTING.preRollMs) / 1000,
    );
    preRoll.push(new Float32Array(chunk));
    preRollSamples += chunk.length;
    while (preRollSamples > maxSamples && preRoll.length > 0) {
      const dropped = preRoll.shift();
      if (dropped) preRollSamples -= dropped.length;
    }
  };

  const startRecorder = () => {
    if (!capture || recording) return;
    pcmChunks = preRoll.length > 0 ? [...preRoll] : [];
    preRoll = [];
    preRollSamples = 0;
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

  const beginPostPlaybackHoldoff = () => {
    ignoreSpeechUntil = performance.now() + POST_PLAYBACK_HOLDOFF_MS;
    if (recording) discardRecorder();
  };

  const triggerBargeIn = () => {
    const levelNow = capture?.readLevel() ?? 0;
    const alreadySpeaking =
      store().patientSpeaking || levelNow >= BARGE_IN_LEVEL * 0.85;
    playback.stop();
    store().markLastAgentTurnInterrupted();
    store().setPhase("INTERRUPTED");
    onBargeIn?.();
    store().setPhase("LISTENING");
    bargeSpeechRun = 0;
    // Keep capturing the interrupting utterance instead of forcing a silence gap.
    if (alreadySpeaking) {
      // Drop any TTS-bleed pre-roll; capture from the interrupt itself.
      preRoll = [];
      preRollSamples = 0;
      bargeArm = "idle";
      ignoreSpeechUntil = 0;
      store().setPatientSpeaking(true);
      if (!recording) startRecorder();
    } else {
      store().setPatientSpeaking(false);
      discardRecorder();
      bargeArm = "wait_silence";
      postBargeSilenceRun = 0;
      ignoreSpeechUntil = performance.now() + 120;
    }
  };

  const poll = () => {
    if (!capture || !vad || paused) return;
    const level = capture.readLevel();
    store().setMicLevel(level);

    const speaking = vad.push(level) === "speech";
    const previous = store().patientSpeaking;
    const phase = store().phase;
    const now = performance.now();
    // Treat local playback as SPEAKING even if the server already said LISTENING.
    const agentAudible = phase === "SPEAKING" || playback.playing;

    // While assistant is speaking, require sustained energy before barge-in.
    if (agentAudible) {
      // New agent turn clears prior post-barge arming so the next interrupt works.
      if (bargeArm !== "idle") {
        bargeArm = "idle";
        postBargeSilenceRun = 0;
      }
      const deliberate =
        level >= BARGE_IN_LEVEL ||
        (speaking && level >= ENDPOINTING.speechThreshold);
      if (deliberate) {
        bargeSpeechRun += 1;
      } else {
        bargeSpeechRun = 0;
      }
      if (bargeSpeechRun >= BARGE_IN_SPEECH_FRAMES) {
        triggerBargeIn();
      }
      return;
    }

    bargeSpeechRun = 0;

    if (now < ignoreSpeechUntil) {
      if (recording) discardRecorder();
      return;
    }

    // Post-barge arming: silence first, then start on the next speech run.
    if (bargeArm === "wait_silence") {
      if (!speaking && level < ENDPOINTING.silenceThreshold) {
        postBargeSilenceRun += 1;
        if (postBargeSilenceRun >= POST_BARGE_SILENCE_FRAMES) {
          bargeArm = "armed";
          postBargeSilenceRun = 0;
        }
      } else {
        postBargeSilenceRun = 0;
      }
      return;
    }

    if (bargeArm === "armed") {
      if (speaking) {
        bargeArm = "idle";
        store().setPatientSpeaking(true);
        startRecorder();
      }
      return;
    }

    if (speaking === previous) {
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
    get paused() {
      return paused;
    },
    async start() {
      paused = false;
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
          if (paused) return;
          const input = event.inputBuffer.getChannelData(0);
          if (!recording) {
            // Do not buffer TTS bleed as "leading speech" for the next utterance.
            const agentAudible =
              store().phase === "SPEAKING" || playback.playing;
            if (agentAudible) {
              preRoll = [];
              preRollSamples = 0;
            } else {
              pushPreRoll(input);
            }
            return;
          }
          pcmChunks.push(new Float32Array(input));
          if (performance.now() - utteranceStartedAt > MAX_UTTERANCE_MS) {
            stopRecorder();
          }
        };
        micSource.connect(processor);
        processor.connect(silent);
        silent.connect(ctx.destination);

        unsubPlayback?.();
        unsubPlayback = playback.subscribe((playing) => {
          if (!playing) beginPostPlaybackHoldoff();
        });

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
    pause() {
      if (!capture || paused) return;
      paused = true;
      if (timer) {
        clearInterval(timer);
        timer = null;
      }
      discardRecorder();
      preRoll = [];
      preRollSamples = 0;
      bargeSpeechRun = 0;
      bargeArm = "idle";
      playback.stop();
      setMicTracksEnabled(false);
      store().setMicLevel(0);
      store().setPatientSpeaking(false);
    },
    resume() {
      if (!capture || !paused) return;
      paused = false;
      setMicTracksEnabled(true);
      vad?.reset();
      if (!timer) {
        timer = setInterval(poll, LEVEL_POLL_MS);
      }
      const phase = store().phase;
      if (phase !== "ENDED" && phase !== "ERROR" && phase !== "IDLE") {
        store().setPhase("LISTENING");
      }
    },
    stop() {
      paused = false;
      if (timer) clearInterval(timer);
      timer = null;
      unsubPlayback?.();
      unsubPlayback = null;
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
      bargeArm = "idle";
      postBargeSilenceRun = 0;
      ignoreSpeechUntil = 0;
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
