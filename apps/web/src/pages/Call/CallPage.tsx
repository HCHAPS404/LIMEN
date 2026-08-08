import { Mic, PanelRight, PhoneOff } from "lucide-react";
import { useState } from "react";

import { StatusChip } from "../../components/data/StatusChip";
import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import { GlassPanel, SolidPanel } from "../../components/glass/Panel";
import { Button } from "../../components/primitives/Button";
import { Drawer } from "../../components/primitives/Drawer";
import { IconButton } from "../../components/primitives/IconButton";
import { WorkspaceSplit } from "../../components/shell/AppShell";
import { CallState } from "../../features/call-session/CallState";
import { LiveContextPanel } from "../../features/call-session/LiveContextPanel";
import { TranscriptTurn } from "../../features/call-session/TranscriptTurn";
import { useCallSession } from "../../features/call-session/useCallSession";
import { VoiceOrb } from "../../features/call-session/VoiceOrb";
import { useIsDesktop } from "../../hooks/useMediaQuery";
import { formatDuration } from "../../lib/format";
import { useCallStore } from "../../state/call-store";

export function CallPage() {
  const { phase, micLevel, elapsed, controls } = useCallSession();
  const error = useCallStore((state) => state.error);
  const transcript = useCallStore((state) => state.transcript);
  const isDesktop = useIsDesktop();
  const [contextOpen, setContextOpen] = useState(false);

  const sessionOpen = phase !== "IDLE" && phase !== "ENDED";

  return (
    <WorkspaceSplit
      inspector={
        isDesktop ? (
          <GlassPanel title="Live context" scroll className="h-full">
            <LiveContextPanel />
          </GlassPanel>
        ) : undefined
      }
    >
      <section
        className="glass-1 sheen-top relative flex shrink-0 flex-col overflow-hidden rounded-2xl"
        aria-label="Call experience"
      >
        <header className="relative z-[2] flex min-h-14 shrink-0 items-center justify-between gap-4 border-b border-glass-border px-6 py-3.5">
          <div className="flex flex-col gap-1">
            <p className="type-eyebrow m-0 text-text-3">Voice</p>
            <h2 className="type-h3 m-0 text-ice">Call experience</h2>
          </div>
          <div className="flex items-center gap-2">
            <StatusChip tone={sessionOpen ? "intelligence" : "neutral"}>
              <span className="type-metric tabular">{formatDuration(elapsed)}</span>
            </StatusChip>
            {!isDesktop && (
              <IconButton
                label="Open live context"
                icon={<PanelRight aria-hidden size={16} strokeWidth={1.5} />}
                onClick={() => setContextOpen(true)}
              />
            )}
          </div>
        </header>

        <div className="relative flex min-h-[min(58vh,28rem)] flex-col items-center justify-end px-6 pb-12 pt-16 md:min-h-[min(62vh,32rem)] md:px-10 md:pb-14 md:pt-20">
          {/* Atmosphere + fused voice field behind the stage copy. */}
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 overflow-hidden"
          >
            <div
              className="absolute inset-0"
              style={{
                background: `
                  radial-gradient(
                    48% 46% at 50% 42%,
                    color-mix(in oklab, var(--limen-action) 12%, transparent),
                    transparent 70%
                  ),
                  radial-gradient(
                    90% 60% at 50% 100%,
                    color-mix(in oklab, var(--limen-bg-0) 80%, transparent),
                    transparent 55%
                  )
                `,
              }}
            />
            <div
              className="absolute left-1/2 top-[38%] flex h-[min(72%,28rem)] w-[min(92%,28rem)] -translate-x-1/2 -translate-y-1/2 items-center justify-center"
              style={{
                maskImage:
                  "radial-gradient(circle at 50% 50%, black 32%, transparent 74%)",
                WebkitMaskImage:
                  "radial-gradient(circle at 50% 50%, black 32%, transparent 74%)",
                opacity: 0.85,
              }}
            >
              <VoiceOrb
                phase={phase}
                level={micLevel}
                className="h-full w-full max-h-none max-w-none"
              />
            </div>
          </div>

          <div className="relative z-[1] flex w-full max-w-[34rem] flex-col items-center gap-8 md:gap-10">
            <CallState phase={phase} />

            {error && (
              <ErrorState
                title="Voice session blocked"
                message={error.message}
                stage={error.code}
                onRetry={() => void controls.start()}
                retryLabel="Request microphone again"
                className="w-full"
              />
            )}

            <div className="flex flex-wrap items-center justify-center gap-4">
              {!sessionOpen ? (
                <Button
                  variant="primary"
                  size="lg"
                  icon={<Mic aria-hidden size={17} strokeWidth={1.75} />}
                  onClick={() => void controls.start()}
                >
                  Start call
                </Button>
              ) : (
                <>
                  <Button
                    variant="secondary"
                    size="lg"
                    icon={<Mic aria-hidden size={17} strokeWidth={1.75} />}
                    disabled
                  >
                    Microphone open
                  </Button>
                  <Button
                    variant="destructive"
                    size="lg"
                    icon={<PhoneOff aria-hidden size={17} strokeWidth={1.75} />}
                    onClick={controls.end}
                  >
                    End session
                  </Button>
                </>
              )}
            </div>

            <p className="type-body-s m-0 max-w-[42ch] text-center leading-relaxed text-text-3">
              Blue reacts to your voice. Orange marks the agent. Transcription
              and clinical reasoning need the voice backend — nothing is
              simulated.
            </p>
          </div>
        </div>
      </section>

      <SolidPanel
        title="Transcript"
        actions={
          <StatusChip>
            <span className="type-metric tabular">
              {transcript.length} {transcript.length === 1 ? "turn" : "turns"}
            </span>
          </StatusChip>
        }
        scroll
        className="min-h-0 flex-1"
      >
        {transcript.length === 0 ? (
          <EmptyState
            eyebrow="Silence"
            title="No turns recorded"
            description="Patient and agent turns appear here as the session progresses, including turns interrupted by barge-in."
          />
        ) : (
          <div className="flex flex-col gap-3">
            {transcript.map((turn) => (
              <TranscriptTurn key={turn.turn_id} turn={turn} />
            ))}
          </div>
        )}
      </SolidPanel>

      {!isDesktop && (
        <Drawer
          open={contextOpen}
          onOpenChange={setContextOpen}
          title="Live context"
        >
          <LiveContextPanel />
        </Drawer>
      )}
    </WorkspaceSplit>
  );
}
