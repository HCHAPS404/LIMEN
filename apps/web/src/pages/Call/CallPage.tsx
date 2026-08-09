import { motion, AnimatePresence } from "framer-motion";
import { Mic, PhoneOff } from "lucide-react";
import { useTranslation } from "react-i18next";

import { StatusChip } from "../../components/data/StatusChip";
import { ConnectionState } from "../../components/feedback/ConnectionState";
import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import { SolidPanel } from "../../components/glass/Panel";
import { Button } from "../../components/primitives/Button";
import { WorkspaceSplit } from "../../components/shell/AppShell";
import { CallState } from "../../features/call-session/CallState";
import { LiveContextPanel } from "../../features/call-session/LiveContextPanel";
import { TranscriptTurn } from "../../features/call-session/TranscriptTurn";
import { useCallSession } from "../../features/call-session/useCallSession";
import { VoiceOrb } from "../../features/call-session/VoiceOrb";
import { formatDuration } from "../../lib/format";
import { useCallStore } from "../../state/call-store";

const ease = [0.22, 0.61, 0.36, 1] as const;

function transportToConnection(
  status: ReturnType<typeof useCallSession>["transportStatus"],
): "connected" | "connecting" | "disconnected" | "unavailable" {
  if (status === "open") return "connected";
  if (status === "connecting") return "connecting";
  if (status === "error") return "disconnected";
  return "unavailable";
}

/**
 * Call stage is an open canvas (orb + phase). Live context and transcript are
 * dense inspectors below — not a stack of decorative glass cages.
 */
export function CallPage() {
  const { t } = useTranslation("call");
  const { phase, micLevel, elapsed, transportStatus, controls } =
    useCallSession();
  const error = useCallStore((state) => state.error);
  const transcript = useCallStore((state) => state.transcript);
  const callId = useCallStore((state) => state.callId);

  const sessionOpen = phase !== "IDLE" && phase !== "ENDED";
  const showRecord = phase !== "IDLE";

  return (
    <WorkspaceSplit scroll="page">
      <section
        className="relative flex flex-col overflow-hidden"
        aria-label={t("stage")}
      >
        <div className="relative z-[2] flex flex-wrap items-center justify-between gap-3 px-1 pb-2">
          <ConnectionState
            status={transportToConnection(transportStatus)}
            detail={
              callId
                ? t(`transport.${transportStatus}`)
                : t("transport.idle")
            }
          />
          <StatusChip tone={sessionOpen ? "intelligence" : "neutral"}>
            <span className="type-metric tabular">{formatDuration(elapsed)}</span>
          </StatusChip>
        </div>

        <div className="relative flex flex-col items-center px-4 pb-10 pt-6 md:px-8 md:pb-12 md:pt-8">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 overflow-hidden"
            style={{
              background: `
                radial-gradient(
                  48% 46% at 50% 28%,
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

          <VoiceOrb
            phase={phase}
            level={micLevel}
            className="relative z-[1] h-[clamp(14rem,32vh,20rem)] w-[clamp(14rem,32vh,20rem)]"
          />

          <div className="relative z-[1] mt-8 flex w-full max-w-[34rem] flex-col items-center gap-6 md:mt-10 md:gap-8">
            <CallState phase={phase} />

            {error && (
              <ErrorState
                title={t("blocked")}
                message={error.message}
                stage={error.code}
                onRetry={() => void controls.start()}
                retryLabel={t("retryMic")}
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
                  {t("start")}
                </Button>
              ) : (
                <Button
                  variant="destructive"
                  size="lg"
                  icon={<PhoneOff aria-hidden size={17} strokeWidth={1.75} />}
                  onClick={controls.end}
                >
                  {t("end")}
                </Button>
              )}
            </div>

            <p className="type-body-s m-0 max-w-[42ch] text-center leading-relaxed text-text-3">
              {t("hint")}
            </p>
          </div>
        </div>
      </section>

      <AnimatePresence initial={false}>
        {showRecord && (
          <motion.div
            key="session-record"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12 }}
            transition={{ duration: 0.4, ease }}
            className="flex flex-col gap-4 md:gap-5"
          >
            <SolidPanel title={t("liveContext")}>
              <LiveContextPanel />
            </SolidPanel>

            <SolidPanel
              title={t("transcript")}
              actions={
                <StatusChip>
                  <span className="type-metric tabular">
                    {t(transcript.length === 1 ? "turns_one" : "turns_other", {
                      count: transcript.length,
                    })}
                  </span>
                </StatusChip>
              }
            >
              {transcript.length === 0 ? (
                <EmptyState
                  eyebrow={t("stage")}
                  title={t("silenceTitle")}
                  description={t("silenceBody")}
                />
              ) : (
                <div className="flex flex-col gap-3">
                  {transcript.map((turn) => (
                    <TranscriptTurn key={turn.turn_id} turn={turn} />
                  ))}
                </div>
              )}
            </SolidPanel>
          </motion.div>
        )}
      </AnimatePresence>
    </WorkspaceSplit>
  );
}
