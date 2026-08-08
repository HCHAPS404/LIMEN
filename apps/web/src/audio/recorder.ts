/** Microphone acquisition and level analysis via Web Audio.
 *  Capture is real; transcription is a backend concern and is never simulated here. */

export type MicPermissionError =
  | "PERMISSION_DENIED"
  | "NO_DEVICE"
  | "UNSUPPORTED"
  | "DEVICE_BUSY"
  | "UNKNOWN";

export class MicrophoneError extends Error {
  readonly reason: MicPermissionError;

  constructor(reason: MicPermissionError, message: string) {
    super(message);
    this.name = "MicrophoneError";
    this.reason = reason;
  }
}

/** Text explanations required by FRONTEND.md section 30. */
export const MIC_ERROR_COPY: Record<MicPermissionError, string> = {
  PERMISSION_DENIED:
    "Microphone access is blocked. Enable microphone permission in your browser and try again.",
  NO_DEVICE:
    "No microphone was detected. Connect an input device and try again.",
  UNSUPPORTED:
    "This browser does not expose microphone capture. Use a recent Chromium, Firefox, or Safari build over HTTPS or localhost.",
  DEVICE_BUSY:
    "The microphone is already in use by another application. Close it and try again.",
  UNKNOWN:
    "The microphone could not be opened. Check your browser input settings and try again.",
};

function classify(error: unknown): MicPermissionError {
  if (!(error instanceof Error)) return "UNKNOWN";
  switch (error.name) {
    case "NotAllowedError":
    case "SecurityError":
      return "PERMISSION_DENIED";
    case "NotFoundError":
    case "OverconstrainedError":
      return "NO_DEVICE";
    case "NotReadableError":
    case "AbortError":
      return "DEVICE_BUSY";
    default:
      return "UNKNOWN";
  }
}

export type MicrophoneCapture = {
  stream: MediaStream;
  context: AudioContext;
  analyser: AnalyserNode;
  /** Time-domain samples in [-1, 1], reused between reads. */
  readWaveform: () => Float32Array;
  /** Root-mean-square level in [0, 1]. */
  readLevel: () => number;
  stop: () => void;
};

export async function openMicrophone(): Promise<MicrophoneCapture> {
  if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
    throw new MicrophoneError("UNSUPPORTED", MIC_ERROR_COPY.UNSUPPORTED);
  }

  let stream: MediaStream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
  } catch (error) {
    const reason = classify(error);
    throw new MicrophoneError(reason, MIC_ERROR_COPY[reason]);
  }

  const context = new AudioContext();
  const source = context.createMediaStreamSource(stream);
  const analyser = context.createAnalyser();
  analyser.fftSize = 2048;
  // Lower smoothing so level spikes reach the voice sphere within a few frames.
  analyser.smoothingTimeConstant = 0.38;
  source.connect(analyser);

  const buffer = new Float32Array(analyser.fftSize);

  return {
    stream,
    context,
    analyser,
    readWaveform: () => {
      analyser.getFloatTimeDomainData(buffer);
      return buffer;
    },
    readLevel: () => {
      analyser.getFloatTimeDomainData(buffer);
      let sum = 0;
      for (let i = 0; i < buffer.length; i += 1) sum += buffer[i] * buffer[i];
      return Math.sqrt(sum / buffer.length);
    },
    stop: () => {
      source.disconnect();
      analyser.disconnect();
      for (const track of stream.getTracks()) track.stop();
      void context.close();
    },
  };
}

/** Permission state without prompting, when the browser supports the query. */
export async function queryMicrophonePermission(): Promise<
  PermissionState | "unsupported"
> {
  if (typeof navigator === "undefined" || !navigator.permissions?.query) {
    return "unsupported";
  }
  try {
    const status = await navigator.permissions.query({
      name: "microphone" as PermissionName,
    });
    return status.state;
  } catch {
    return "unsupported";
  }
}
