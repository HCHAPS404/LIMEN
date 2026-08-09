/** Encode mono PCM float samples as 16-bit little-endian WAV (no deps). */

export const CANONICAL_SAMPLE_RATE = 16_000;

export function downsampleTo16k(
  samples: Float32Array,
  sourceRate: number,
): Float32Array {
  if (sourceRate === CANONICAL_SAMPLE_RATE || samples.length === 0) {
    return samples;
  }
  const ratio = sourceRate / CANONICAL_SAMPLE_RATE;
  const outLen = Math.max(1, Math.floor(samples.length / ratio));
  const out = new Float32Array(outLen);
  for (let i = 0; i < outLen; i += 1) {
    const src = i * ratio;
    const left = Math.floor(src);
    const right = Math.min(left + 1, samples.length - 1);
    const frac = src - left;
    out[i] = samples[left] * (1 - frac) + samples[right] * frac;
  }
  return out;
}

export function encodeWavPcm16Mono(
  samples: Float32Array,
  sampleRate = CANONICAL_SAMPLE_RATE,
): ArrayBuffer {
  const numSamples = samples.length;
  const bytesPerSample = 2;
  const blockAlign = bytesPerSample; // mono
  const dataSize = numSamples * bytesPerSample;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  const writeStr = (offset: number, text: string) => {
    for (let i = 0; i < text.length; i += 1) {
      view.setUint8(offset + i, text.charCodeAt(i));
    }
  };

  writeStr(0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeStr(8, "WAVE");
  writeStr(12, "fmt ");
  view.setUint32(16, 16, true); // PCM chunk size
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * blockAlign, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, 16, true);
  writeStr(36, "data");
  view.setUint32(40, dataSize, true);

  let offset = 44;
  for (let i = 0; i < numSamples; i += 1) {
    const clamped = Math.max(-1, Math.min(1, samples[i]));
    const int16 = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;
    view.setInt16(offset, int16, true);
    offset += 2;
  }
  return buffer;
}

export function floatChunksToWav(
  chunks: Float32Array[],
  sourceRate: number,
): Blob {
  const total = chunks.reduce((sum, c) => sum + c.length, 0);
  const merged = new Float32Array(total);
  let o = 0;
  for (const chunk of chunks) {
    merged.set(chunk, o);
    o += chunk.length;
  }
  const resampled = downsampleTo16k(merged, sourceRate);
  const wav = encodeWavPcm16Mono(resampled, CANONICAL_SAMPLE_RATE);
  return new Blob([wav], { type: "audio/wav" });
}
