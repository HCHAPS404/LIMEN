/** Single-voice playback queue for synthesized agent turns.
 *  Agent audio arrives from the backend TTS provider; nothing is generated here.
 *  `stop()` is the barge-in primitive: two voices must never overlap. */

export type PlaybackListener = (playing: boolean) => void;

export type AgentPlayback = {
  enqueue: (audio: Blob | string) => Promise<void>;
  stop: () => void;
  readonly playing: boolean;
  subscribe: (listener: PlaybackListener) => () => void;
  dispose: () => void;
};

export function createAgentPlayback(): AgentPlayback {
  const element = typeof Audio === "undefined" ? null : new Audio();
  const listeners = new Set<PlaybackListener>();
  let playing = false;
  let objectUrl: string | null = null;

  const emit = (next: boolean) => {
    playing = next;
    for (const listener of listeners) listener(next);
  };

  const releaseUrl = () => {
    if (objectUrl) {
      URL.revokeObjectURL(objectUrl);
      objectUrl = null;
    }
  };

  element?.addEventListener("ended", () => {
    releaseUrl();
    emit(false);
  });

  return {
    async enqueue(audio) {
      if (!element) return;
      // A new turn always replaces the current one; overlapping voices are a defect.
      element.pause();
      releaseUrl();

      if (typeof audio === "string") {
        element.src = audio;
      } else {
        objectUrl = URL.createObjectURL(audio);
        element.src = objectUrl;
      }

      emit(true);
      try {
        await element.play();
      } catch {
        releaseUrl();
        emit(false);
      }
    },
    stop() {
      if (!element) return;
      element.pause();
      element.currentTime = 0;
      releaseUrl();
      emit(false);
    },
    get playing() {
      return playing;
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    dispose() {
      element?.pause();
      releaseUrl();
      listeners.clear();
      playing = false;
    },
  };
}
