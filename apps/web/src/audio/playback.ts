/** Single-voice playback queue for synthesized agent turns.
 *  Agent audio arrives from the backend TTS provider; nothing is generated here.
 *  `stop()` is the barge-in primitive: two voices must never overlap. */

export type PlaybackListener = (playing: boolean) => void;

export type PlaybackMeta = {
  turnSeq?: number;
};

export type AgentPlayback = {
  enqueue: (audio: Blob | string, meta?: PlaybackMeta) => Promise<void>;
  stop: () => void;
  readonly playing: boolean;
  readonly activeTurnSeq: number | null;
  onPlaybackStarted: ((meta: {
    turnSeq: number | null;
    agentAudioStartedMonotonic: number;
    agentAudioReceivedMonotonic: number;
  }) => void) | null;
  onPlaybackCompleted: ((meta: { turnSeq: number | null }) => void) | null;
  subscribe: (listener: PlaybackListener) => () => void;
  dispose: () => void;
};

export function createAgentPlayback(): AgentPlayback {
  const element = typeof Audio === "undefined" ? null : new Audio();
  const listeners = new Set<PlaybackListener>();
  let playing = false;
  let objectUrl: string | null = null;
  let activeTurnSeq: number | null = null;
  let generation = 0;
  let onPlaybackStarted: AgentPlayback["onPlaybackStarted"] = null;
  let onPlaybackCompleted: AgentPlayback["onPlaybackCompleted"] = null;

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
    const seq = activeTurnSeq;
    releaseUrl();
    emit(false);
    onPlaybackCompleted?.({ turnSeq: seq });
    activeTurnSeq = null;
  });

  return {
    get onPlaybackStarted() {
      return onPlaybackStarted;
    },
    set onPlaybackStarted(handler) {
      onPlaybackStarted = handler;
    },
    get onPlaybackCompleted() {
      return onPlaybackCompleted;
    },
    set onPlaybackCompleted(handler) {
      onPlaybackCompleted = handler;
    },
    get activeTurnSeq() {
      return activeTurnSeq;
    },
    async enqueue(audio, meta) {
      if (!element) return;
      const gen = ++generation;
      const turnSeq = meta?.turnSeq ?? null;
      const receivedMono = performance.now() / 1000;
      // A new turn always replaces the current one; overlapping voices are a defect.
      element.pause();
      releaseUrl();
      activeTurnSeq = turnSeq;

      if (typeof audio === "string") {
        element.src = audio;
      } else {
        objectUrl = URL.createObjectURL(audio);
        element.src = objectUrl;
      }

      emit(true);
      try {
        await element.play();
        if (gen !== generation) return; // superseded
        onPlaybackStarted?.({
          turnSeq,
          agentAudioReceivedMonotonic: receivedMono,
          agentAudioStartedMonotonic: performance.now() / 1000,
        });
      } catch {
        if (gen !== generation) return;
        releaseUrl();
        emit(false);
        activeTurnSeq = null;
      }
    },
    stop() {
      generation += 1;
      if (!element) return;
      const seq = activeTurnSeq;
      const wasPlaying = playing;
      element.pause();
      element.currentTime = 0;
      releaseUrl();
      emit(false);
      activeTurnSeq = null;
      // Barge-in path: notify completion so holdoffs / server LISTENING stay aligned.
      if (wasPlaying) {
        onPlaybackCompleted?.({ turnSeq: seq });
      }
    },
    get playing() {
      return playing;
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    dispose() {
      generation += 1;
      try {
        element?.pause();
      } catch {
        // jsdom may not implement HTMLMediaElement.pause.
      }
      releaseUrl();
      listeners.clear();
      playing = false;
      activeTurnSeq = null;
    },
  };
}
