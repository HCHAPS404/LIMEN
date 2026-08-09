import { describe, expect, it } from "vitest";

import { downsampleTo16k, encodeWavPcm16Mono } from "./wav";

describe("wav encoder", () => {
  it("encodes a RIFF/WAVE header for mono pcm16", () => {
    const samples = new Float32Array(160); // 10ms @ 16k
    const buf = encodeWavPcm16Mono(samples, 16_000);
    const bytes = new Uint8Array(buf);
    expect(String.fromCharCode(...bytes.slice(0, 4))).toBe("RIFF");
    expect(String.fromCharCode(...bytes.slice(8, 12))).toBe("WAVE");
  });

  it("downsamples without inventing length explosions", () => {
    const src = new Float32Array(48_000);
    const out = downsampleTo16k(src, 48_000);
    expect(out.length).toBe(16_000);
  });
});
