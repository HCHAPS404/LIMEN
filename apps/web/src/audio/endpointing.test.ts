/** Endpointing defaults — pause-heavy Spanish over minimum latency. */
import { describe, expect, it } from "vitest";

import { ENDPOINTING, createVad } from "./vad";

describe("PHASE 6.3 endpointing defaults", () => {
  it("uses longer silence-to-end than a single pause (~1.6s)", () => {
    expect(ENDPOINTING.silenceFrames * ENDPOINTING.levelPollMs).toBeGreaterThanOrEqual(
      1500,
    );
  });

  it("requires sustained speech for barge-in gating config", () => {
    expect(ENDPOINTING.bargeInSpeechFrames * ENDPOINTING.levelPollMs).toBeGreaterThanOrEqual(
      400,
    );
  });

  it("does not end speech after a short intra-phrase pause", () => {
    const vad = createVad({
      speechFrames: ENDPOINTING.speechFrames,
      silenceFrames: ENDPOINTING.silenceFrames,
    });
    for (let i = 0; i < ENDPOINTING.speechFrames; i += 1) vad.push(0.2);
    expect(vad.state).toBe("speech");
    // ~840 ms pause (14 frames) must not end the utterance.
    for (let i = 0; i < 14; i += 1) vad.push(0.001);
    expect(vad.state).toBe("speech");
  });
});
