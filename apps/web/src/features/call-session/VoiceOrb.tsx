import { useEffect, useRef } from "react";

import type { CallPhase } from "../../api/types";
import { cn } from "../../lib/cn";
import { voiceEnergy, voiceRoleFromPhase, type VoiceRole } from "./voiceRole";

type Point3 = { x: number; y: number; z: number };

const PHI = Math.PI * (3 - Math.sqrt(5));
const POINT_COUNT = 780;

function fibonacciSphere(count: number): Point3[] {
  const points: Point3[] = [];
  for (let i = 0; i < count; i += 1) {
    const y = 1 - (i / (count - 1)) * 2;
    const radius = Math.sqrt(Math.max(0, 1 - y * y));
    const theta = PHI * i;
    points.push({
      x: Math.cos(theta) * radius,
      y,
      z: Math.sin(theta) * radius,
    });
  }
  return points;
}

function parseCssColor(value: string): [number, number, number] {
  const hex = value.trim();
  if (hex.startsWith("#") && (hex.length === 7 || hex.length === 4)) {
    if (hex.length === 4) {
      const r = Number.parseInt(hex[1] + hex[1], 16);
      const g = Number.parseInt(hex[2] + hex[2], 16);
      const b = Number.parseInt(hex[3] + hex[3], 16);
      return [r, g, b];
    }
    return [
      Number.parseInt(hex.slice(1, 3), 16),
      Number.parseInt(hex.slice(3, 5), 16),
      Number.parseInt(hex.slice(5, 7), 16),
    ];
  }
  const rgb = hex.match(/rgba?\(([^)]+)\)/);
  if (rgb) {
    const parts = rgb[1].split(",").map((part) => Number.parseFloat(part.trim()));
    return [parts[0] ?? 200, parts[1] ?? 200, parts[2] ?? 200];
  }
  return [200, 208, 216];
}

function mixRgb(
  a: [number, number, number],
  b: [number, number, number],
  t: number,
): [number, number, number] {
  const k = Math.min(1, Math.max(0, t));
  return [
    Math.round(a[0] + (b[0] - a[0]) * k),
    Math.round(a[1] + (b[1] - a[1]) * k),
    Math.round(a[2] + (b[2] - a[2]) * k),
  ];
}

function rgba(rgb: [number, number, number], alpha: number): string {
  return `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${alpha})`;
}

type Palette = {
  base: [number, number, number];
  soft: [number, number, number];
  white: [number, number, number];
};

function paletteForRole(role: VoiceRole, styles: CSSStyleDeclaration): Palette {
  const white = parseCssColor(styles.getPropertyValue("--limen-white"));
  if (role === "patient") {
    return {
      base: parseCssColor(styles.getPropertyValue("--limen-voice-patient")),
      soft: parseCssColor(styles.getPropertyValue("--limen-voice-patient-soft")),
      white,
    };
  }
  if (role === "agent") {
    return {
      base: parseCssColor(styles.getPropertyValue("--limen-voice-agent")),
      soft: parseCssColor(styles.getPropertyValue("--limen-voice-agent-soft")),
      white,
    };
  }
  if (role === "processing") {
    return {
      base: parseCssColor(styles.getPropertyValue("--limen-ice")),
      soft: parseCssColor(styles.getPropertyValue("--limen-text-2")),
      white,
    };
  }
  return {
    base: parseCssColor(styles.getPropertyValue("--limen-voice-idle")),
    soft: parseCssColor(styles.getPropertyValue("--limen-text-3")),
    white,
  };
}

/** Reactive particle sphere. Canvas-driven so audio motion never re-renders React.
 *  Patient speech → blue→white; agent speech → orange→white; idle → silver mesh. */
export function VoiceOrb({
  phase,
  level = 0,
  className,
}: {
  phase: CallPhase;
  level?: number;
  className?: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const phaseRef = useRef(phase);
  const levelRef = useRef(level);
  phaseRef.current = phase;
  levelRef.current = level;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext("2d");
    if (!context) return;

    const points = fibonacciSphere(POINT_COUNT);
    let styles = getComputedStyle(canvas);
    let frame = 0;
    const start = performance.now();
    let rotY = 0;
    let rotX = 0.18;
    // Smooth energy so the mesh breathes instead of stuttering with RMS noise.
    let smoothed = 0;

    const resize = () => {
      const ratio = window.devicePixelRatio || 1;
      const { width, height } = canvas.getBoundingClientRect();
      canvas.width = Math.max(1, Math.floor(width * ratio));
      canvas.height = Math.max(1, Math.floor(height * ratio));
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      styles = getComputedStyle(canvas);
    };

    const draw = (now: number) => {
      const { width, height } = canvas.getBoundingClientRect();
      const role = voiceRoleFromPhase(phaseRef.current);
      const target = voiceEnergy(role, levelRef.current, now - start);
      // Attack faster than release so speech onset is obvious.
      const follow = target > smoothed ? 0.5 : 0.14;
      smoothed += (target - smoothed) * follow;
      const energy = smoothed;
      const palette = paletteForRole(role, styles);
      const cx = width / 2;
      const cy = height / 2;
      // Keep base radius small enough that peak displace × scale stays on-canvas.
      const radius = Math.min(width, height) * 0.3;

      rotY += 0.0035 + energy * 0.016;
      rotX = 0.15 + Math.sin((now - start) * 0.00045) * (0.05 + energy * 0.04);

      // Full clear to transparent — never paint a rectangular slab, or the
      // canvas reads as a square over the page atmosphere.
      context.clearRect(0, 0, width, height);

      // Glow must die to zero alpha inside a circle that fits the canvas.
      // fillRect + a large radial used to leave a visible box at the edges.
      const glowOuter = Math.min(width, height) * 0.48;
      const glow = context.createRadialGradient(
        cx,
        cy,
        radius * 0.12,
        cx,
        cy,
        glowOuter,
      );
      const glowAlpha = role === "idle" ? 0.07 : 0.14 + energy * 0.3;
      glow.addColorStop(0, rgba(palette.base, glowAlpha));
      glow.addColorStop(0.42, rgba(palette.soft, glowAlpha * 0.38));
      glow.addColorStop(0.72, rgba(palette.soft, glowAlpha * 0.1));
      // Match RGB on the transparent stop so canvas does not tint edges black.
      glow.addColorStop(1, rgba(palette.soft, 0));
      context.beginPath();
      context.arc(cx, cy, glowOuter, 0, Math.PI * 2);
      context.fillStyle = glow;
      context.fill();

      const cosY = Math.cos(rotY);
      const sinY = Math.sin(rotY);
      const cosX = Math.cos(rotX);
      const sinX = Math.sin(rotX);

      type Projected = {
        x: number;
        y: number;
        z: number;
        size: number;
        color: string;
      };
      const projected: Projected[] = [];
      const t = now - start;

      for (let i = 0; i < points.length; i += 1) {
        const p = points[i];
        // Ripple folds the surface; amplitude is capped so loud speech never
        // pushes points past the canvas edge.
        const rippleA =
          Math.sin(p.y * 7 + t * 0.0045) * Math.cos(p.x * 5 + rotY * 2.4);
        const rippleB = Math.sin(p.z * 5 - t * 0.0032 + p.x * 3);
        const displace =
          1 + energy * (0.1 + 0.18 * rippleA + 0.12 * rippleB);
        const x = p.x * displace;
        const y = p.y * displace;
        const z = p.z * displace;

        const x1 = x * cosY - z * sinY;
        const z1 = x * sinY + z * cosY;
        const y1 = y * cosX - z1 * sinX;
        const z2 = y * sinX + z1 * cosX;

        const depth = (z2 + 1.4) / 2.4;
        const scale = 0.82 + energy * 0.24;
        const px = cx + x1 * radius * scale;
        const py = cy + y1 * radius * scale;
        const towardWhite = Math.min(1, depth * 0.5 + energy * 0.45);
        const rgb = mixRgb(palette.base, palette.white, towardWhite);
        const alpha =
          role === "idle"
            ? 0.24 + depth * 0.5
            : 0.38 + depth * 0.5 + energy * 0.22;

        projected.push({
          x: px,
          y: py,
          z: z2,
          size: (0.75 + depth * 1.7) * (0.9 + energy * 0.45),
          color: rgba(rgb, alpha),
        });
      }

      projected.sort((a, b) => a.z - b.z);

      context.lineWidth = 0.65;
      for (let i = 0; i < projected.length; i += 6) {
        const a = projected[i];
        const b = projected[Math.min(projected.length - 1, i + 13)];
        const c = projected[Math.min(projected.length - 1, i + 27)];
        if (a.z < -0.2) continue;
        context.strokeStyle = rgba(
          mixRgb(palette.base, palette.white, 0.4),
          role === "idle" ? 0.07 : 0.11 + energy * 0.14,
        );
        context.beginPath();
        context.moveTo(a.x, a.y);
        context.lineTo(b.x, b.y);
        context.moveTo(a.x, a.y);
        context.lineTo(c.x, c.y);
        context.stroke();
      }

      for (const point of projected) {
        context.fillStyle = point.color;
        context.beginPath();
        context.arc(point.x, point.y, point.size, 0, Math.PI * 2);
        context.fill();
      }

      frame = window.requestAnimationFrame(draw);
    };

    resize();
    window.addEventListener("resize", resize);
    frame = window.requestAnimationFrame(draw);

    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
    };
  }, []);

  const role = voiceRoleFromPhase(phase);
  const label =
    role === "patient"
      ? "Patient voice field"
      : role === "agent"
        ? "Agent voice field"
        : "Voice field at rest";

  return (
    <canvas
      ref={canvasRef}
      role="img"
      aria-label={label}
      className={cn(
        "block bg-transparent",
        // Callers that fuse the orb into a background pass their own size.
        className ?? "h-[clamp(14rem,34vh,22rem)] w-[clamp(14rem,34vh,22rem)]",
      )}
    />
  );
}
