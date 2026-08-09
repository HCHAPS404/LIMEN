import { describe, expect, it } from "vitest";

import { createVad } from "./vad";

const feed = (
  vad: ReturnType<typeof createVad>,
  level: number,
  frames: number,
) => {
  for (let i = 0; i < frames; i += 1) vad.push(level);
};

describe("voice activity detection", () => {
  it("starts in silence", () => {
    expect(createVad().state).toBe("silence");
  });

  it("needs sustained energy before declaring speech", () => {
    const vad = createVad({ speechThreshold: 0.05, speechFrames: 3 });

    expect(vad.push(0.2)).toBe("silence");
    expect(vad.push(0.2)).toBe("silence");
    expect(vad.push(0.2)).toBe("speech");
  });

  it("holds speech through brief dips so barge-in does not flicker", () => {
    const vad = createVad({ speechFrames: 2, silenceFrames: 5 });
    feed(vad, 0.3, 3);

    feed(vad, 0.001, 3);
    expect(vad.state).toBe("speech");

    feed(vad, 0.001, 3);
    expect(vad.state).toBe("silence");
  });

  it("ignores levels inside the hysteresis band", () => {
    const vad = createVad({ speechThreshold: 0.06, silenceThreshold: 0.02 });
    feed(vad, 0.04, 20);

    expect(vad.state).toBe("silence");
  });

  it("resets to silence", () => {
    const vad = createVad({ speechFrames: 1 });
    vad.push(0.5);
    expect(vad.state).toBe("speech");

    vad.reset();
    expect(vad.state).toBe("silence");
  });
});
