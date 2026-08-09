/** Endpointing defaults — pause-heavy Spanish over minimum latency. */
import { describe, expect, it } from "vitest";

import { ENDPOINTING, createVad } from "./vad";

describe("PHASE 6.3 endpointing defaults", () => {
  it("uses silence-to-end long enough for talkative pauses (~1.8s)", () => {
    expect(ENDPOINTING.silenceFrames * ENDPOINTING.levelPollMs).toBeGreaterThanOrEqual(
      1800,
    );
    expect(ENDPOINTING.maxUtteranceMs).toBeGreaterThanOrEqual(60_000);
  });

  it("requires sustained speech for barge-in gating config", () => {
    expect(ENDPOINTING.bargeInSpeechFrames * ENDPOINTING.levelPollMs).toBeGreaterThanOrEqual(
      480,
    );
    expect(ENDPOINTING.bargeInSpeechThreshold).toBeGreaterThan(ENDPOINTING.speechThreshold);
  });

  it("keeps a pre-roll window so leading syllables are not clipped", () => {
    expect(ENDPOINTING.preRollMs).toBeGreaterThanOrEqual(300);
    expect(ENDPOINTING.speechFrames).toBeLessThanOrEqual(3);
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
