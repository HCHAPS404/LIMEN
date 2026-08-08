import { Mic, MicOff } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { ErrorState } from "../../components/feedback/ErrorState";
import { Button } from "../../components/primitives/Button";
import {
  MIC_ERROR_COPY,
  MicrophoneError,
  openMicrophone,
  queryMicrophonePermission,
  type MicrophoneCapture,
} from "../../audio/recorder";
import { cn } from "../../lib/cn";

/** Real capture test: opens the device, reports the measured level, then releases it. */
export function MicDiagnostics() {
  const captureRef = useRef<MicrophoneCapture | null>(null);
  const [permission, setPermission] = useState<PermissionState | "unsupported">(
    "unsupported",
  );
  const [level, setLevel] = useState(0);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void queryMicrophonePermission().then((state) => {
      if (!cancelled) setPermission(state);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!testing) return;
    const timer = setInterval(() => {
      setLevel(captureRef.current?.readLevel() ?? 0);
    }, 80);
    return () => clearInterval(timer);
  }, [testing]);

  useEffect(() => {
    return () => {
      captureRef.current?.stop();
      captureRef.current = null;
    };
  }, []);

  const start = async () => {
    setError(null);
    try {
      captureRef.current = await openMicrophone();
      setTesting(true);
      setPermission("granted");
    } catch (cause) {
      const reason = cause instanceof MicrophoneError ? cause.reason : "UNKNOWN";
      setError(MIC_ERROR_COPY[reason]);
      if (reason === "PERMISSION_DENIED") setPermission("denied");
    }
  };

  const stop = () => {
    captureRef.current?.stop();
    captureRef.current = null;
    setTesting(false);
    setLevel(0);
  };

  const permissionLabel: Record<PermissionState | "unsupported", string> = {
    granted: "Granted",
    denied: "Blocked",
    prompt: "Will prompt",
    unsupported: "Not reported by this browser",
  };

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-[minmax(7rem,0.42fr)_minmax(0,1fr)] items-baseline gap-x-6 border-b border-glass-border py-3.5">
        <span className="type-label">Permission</span>
        <span
          className={cn(
            "text-right text-[0.9375rem]",
            permission === "denied" ? "text-coral" : "text-ice",
          )}
        >
          {permissionLabel[permission]}
        </span>
      </div>

      <div className="flex flex-col gap-3 border-b border-glass-border pb-4">
        <div className="grid grid-cols-[minmax(7rem,0.42fr)_minmax(0,1fr)] items-baseline gap-x-6">
          <span className="type-label">Measured input level</span>
          <span className="type-metric text-right text-[0.875rem] text-ice">
            {testing ? `${Math.round(Math.min(1, level * 4) * 100)}%` : "—"}
          </span>
        </div>
        <div
          className="h-1.5 overflow-hidden rounded-full bg-[var(--glass-highlight)]"
          role="meter"
          aria-label="Microphone input level"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={testing ? Math.round(Math.min(1, level * 4) * 100) : 0}
        >
          <div
            className="h-full rounded-full bg-ice/70 transition-[width] duration-[var(--motion-fast)]"
            style={{ width: `${Math.min(1, level * 4) * 100}%` }}
          />
        </div>
      </div>

      {error && <ErrorState title="Microphone test failed" message={error} />}

      <div>
        {testing ? (
          <Button
            variant="secondary"
            size="sm"
            icon={<MicOff aria-hidden size={14} strokeWidth={1.5} />}
            onClick={stop}
          >
            Stop test
          </Button>
        ) : (
          <Button
            variant="secondary"
            size="sm"
            icon={<Mic aria-hidden size={14} strokeWidth={1.5} />}
            onClick={() => void start()}
          >
            Test microphone
          </Button>
        )}
      </div>
    </div>
  );
}
