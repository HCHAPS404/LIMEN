import { useEffect, useRef } from "react";

import { cn } from "../../lib/cn";

type WaveformProps = {
  /** Pulls time-domain samples straight from the analyser. `null` means no
   *  live capture, and the component draws a flat baseline instead of noise. */
  readWaveform: (() => Float32Array) | null;
  active: boolean;
  className?: string;
};

/** Canvas visualization driven by its own animation frame loop so audio
 *  rendering never re-renders the React tree (FRONTEND.md section 31). */
export function Waveform({ readWaveform, active, className }: WaveformProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    let context: CanvasRenderingContext2D | null = null;
    try {
      context = canvas.getContext("2d");
    } catch {
      return;
    }
    if (!context) return;

    let frame = 0;
    const styles = getComputedStyle(canvas);
    const accent = styles.getPropertyValue("--limen-cyan").trim();
    const idle = styles.getPropertyValue("--limen-text-3").trim();

    const resize = () => {
      const ratio = window.devicePixelRatio || 1;
      const { width, height } = canvas.getBoundingClientRect();
      canvas.width = Math.max(1, Math.floor(width * ratio));
      canvas.height = Math.max(1, Math.floor(height * ratio));
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
    };

    const draw = () => {
      const { width, height } = canvas.getBoundingClientRect();
      const middle = height / 2;
      context.clearRect(0, 0, width, height);
      context.lineWidth = 1.25;
      context.lineJoin = "round";
      context.strokeStyle = active && readWaveform ? accent : idle;
      context.globalAlpha = active && readWaveform ? 0.9 : 0.35;
      context.beginPath();

      const samples = readWaveform?.();
      if (samples && active) {
        const step = Math.max(1, Math.floor(samples.length / width));
        for (let x = 0; x < width; x += 1) {
          const sample = samples[Math.min(samples.length - 1, x * step)] ?? 0;
          const y = middle - sample * middle * 0.9;
          if (x === 0) context.moveTo(x, y);
          else context.lineTo(x, y);
        }
      } else {
        context.moveTo(0, middle);
        context.lineTo(width, middle);
      }

      context.stroke();
      frame = window.requestAnimationFrame(draw);
    };

    resize();
    window.addEventListener("resize", resize);
    frame = window.requestAnimationFrame(draw);

    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
    };
  }, [readWaveform, active]);

  return (
    <canvas
      ref={canvasRef}
      role="img"
      aria-label={
        active
          ? "Live microphone waveform"
          : "Microphone inactive, flat waveform baseline"
      }
      className={cn("h-14 w-full", className)}
    />
  );
}
