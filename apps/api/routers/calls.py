"""Call HTTP and WebSocket transport — voice wraps the authoritative text-turn path."""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status

from apps.api.dependencies import CallSvc, CurrentAccount, settings_dependency
from apps.api.schemas.calls import (
    CallDetailResponse,
    CallSummaryResponse,
    ClinicalStatePayload,
    CreateCallRequest,
    EvidenceChunkPayload,
    SafetyTurnPayload,
    TextTurnRequest,
    TextTurnResponse,
)
from limen.auth import AuthService, SessionInvalid
from limen.conversation.call_service import CallService
from limen.conversation.session_intent import (
    idle_check_reply,
    idle_timeout_farewell,
    max_duration_farewell,
)
from limen.intelligence.providers.factory import build_llm_provider
from limen.persistence.database import get_database
from limen.persistence.repositories import (
    SqliteAccountRepository,
    SqliteCallRepository,
    SqliteTraceRepository,
)
from limen.telemetry.aggregates import aggregate_call_metrics, turn_metrics_from_dict
from limen.telemetry.browser_voice import blocking_e2e_reasons
from limen.voice.audio_codec import AudioFormatError, normalize_transcript_text
from limen.voice.pipeline import (
    compute_voice_response_latency_ms,
    synthesize_with_timing,
    timing_to_metrics,
    transcribe_with_timing,
)
from limen.voice.stt import build_stt_provider
from limen.voice.timing_record import VoiceTurnTimingRecord
from limen.voice.transcript_quality import is_likely_stt_hallucination
from limen.voice.tts import build_tts_provider

router = APIRouter(prefix="/api/calls", tags=["calls"])

# Premium call lifecycle — keep sessions from hanging forever (cost + UX).
_IDLE_PROMPT_S = 150.0
_IDLE_HANGUP_AFTER_PROMPT_S = 90.0
_MAX_CALL_DURATION_S = 15 * 60.0
_PLAYBACK_END_FAILSAFE_S = 8.0
_WS_POLL_S = 5.0


def _call_not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"code": "call_not_found", "message": "Call not found"},
    )


@router.get("", response_model=list[CallSummaryResponse])
async def list_calls(account: CurrentAccount, calls: CallSvc) -> list[CallSummaryResponse]:
    return [CallSummaryResponse.model_validate(item) for item in calls.list(account.account_id)]


@router.post("", response_model=CallSummaryResponse, status_code=status.HTTP_201_CREATED)
async def create_call(
    payload: CreateCallRequest,
    account: CurrentAccount,
    calls: CallSvc,
) -> CallSummaryResponse:
    created = calls.create(
        account_id=account.account_id,
        patient_alias=payload.patient_alias,
        procedure=payload.procedure,
        postoperative_day=payload.postoperative_day,
        voice_persona=payload.voice_persona,
    )
    return CallSummaryResponse.model_validate(created)


@router.get("/{call_id}", response_model=CallSummaryResponse)
async def get_call(
    call_id: str,
    account: CurrentAccount,
    calls: CallSvc,
) -> CallSummaryResponse:
    found = calls.get(account.account_id, call_id)
    if found is None:
        raise _call_not_found()
    return CallSummaryResponse.model_validate(found)


@router.post("/{call_id}/turns", response_model=TextTurnResponse)
async def post_text_turn(
    call_id: str,
    payload: TextTurnRequest,
    account: CurrentAccount,
    calls: CallSvc,
) -> TextTurnResponse:
    try:
        result = await calls.process_text_turn(
            account_id=account.account_id,
            call_id=call_id,
            user_text=payload.text,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "invalid_call_state", "message": str(error)},
        ) from error
    if result is None:
        raise _call_not_found()
    return TextTurnResponse(
        assistant_text=result.assistant_text,
        clinical_state=ClinicalStatePayload.model_validate(
            result.clinical_state.model_dump(mode="json")
        ),
        safety=SafetyTurnPayload(
            risk=result.safety.severity.name,  # type: ignore[arg-type]
            escalate=result.safety.escalate,
            reasons=list(result.safety.reasons),
            policy_version=result.safety.policy_version,
        ),
        evidence=[
            EvidenceChunkPayload.model_validate(chunk.model_dump(mode="json"))
            for chunk in result.evidence
        ],
        metrics=result.metrics,
    )


@router.post("/{call_id}/finish", response_model=CallSummaryResponse)
async def finish_call(
    call_id: str,
    account: CurrentAccount,
    calls: CallSvc,
) -> CallSummaryResponse:
    finished = calls.finish(account_id=account.account_id, call_id=call_id)
    if finished is None:
        raise _call_not_found()
    return CallSummaryResponse.model_validate(finished)


@router.get("/{call_id}/summary", response_model=CallDetailResponse)
async def call_summary(
    call_id: str,
    account: CurrentAccount,
    calls: CallSvc,
) -> CallDetailResponse:
    payload = calls.summary(account.account_id, call_id)
    if payload is None:
        raise _call_not_found()
    return CallDetailResponse(
        call=CallSummaryResponse.model_validate(payload["call"]),
        summary=payload["summary"],
        clinical_state=payload["clinical_state"],
        metrics=payload["metrics"],
        turns=payload["turns"],
    )


def _event(
    *,
    type_: str,
    call_id: str,
    sequence: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "type": type_,
        "call_id": call_id,
        "sequence": sequence,
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "payload": payload,
    }


def _tmp_voice_dir(settings: Any) -> Path:
    path = Path(settings.log_path).parent / "tmp" / "voice"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_transient_voice_wav(settings: Any, *, call_id: str, turn_seq: int, audio: bytes) -> Path:
    """Persist raw utterance briefly for STT; caller must delete (privacy)."""
    path = _tmp_voice_dir(settings) / f"{call_id}-{turn_seq}.wav"
    path.write_bytes(audio)
    return path


def _cleanup_transient_voice_wav(path: Path | None) -> None:
    if path is None:
        return
    with contextlib.suppress(OSError):
        path.unlink(missing_ok=True)


def _record_voice_sample(
    *,
    service: CallService,
    account_id: str,
    call_id: str,
    latency_ms: float,
    interruptions: int = 0,
    stt_errors: int = 0,
    tts_errors: int = 0,
) -> None:
    row = service._calls.get_call_row(account_id, call_id)  # noqa: SLF001
    if row is None:
        return
    blob = service._load_call_metrics_blob(row)  # noqa: SLF001
    samples = list(blob.get("voice_latencies_ms") or [])
    samples.append(float(latency_ms))
    turns = list(blob.get("turns") or [])
    call_agg = aggregate_call_metrics(
        [turn_metrics_from_dict(t) if isinstance(t, dict) else t for t in turns],
        final_risk=row["final_risk"],
        escalated=bool(row["escalated"]),
        voice_latencies_ms=samples,
        voice_interruptions=int(blob.get("voice_interruptions") or 0) + interruptions,
        stt_errors=int(blob.get("stt_errors") or 0) + stt_errors,
        tts_errors=int(blob.get("tts_errors") or 0) + tts_errors,
    )
    blob["voice_latencies_ms"] = samples
    blob["voice_interruptions"] = call_agg.voice_interruptions
    blob["stt_errors"] = call_agg.stt_errors
    blob["tts_errors"] = call_agg.tts_errors
    blob["call"] = call_agg.model_dump(mode="json")
    from limen.clinical.state import ClinicalState

    clinical = ClinicalState.model_validate_json(row["clinical_state_json"] or "{}")
    service._calls.update_runtime(  # noqa: SLF001
        account_id=account_id,
        call_id=call_id,
        clinical_state=clinical,
        final_risk=row["final_risk"],
        escalated=bool(row["escalated"]),
        metrics=blob,
    )


@router.websocket("/{call_id}/stream")
async def call_stream(websocket: WebSocket, call_id: str) -> None:
    """Realtime voice/text session. Binary audio → STT → process_text_turn → TTS."""
    await websocket.accept()
    settings = settings_dependency()
    database = get_database(settings)
    auth = AuthService(
        SqliteAccountRepository(database),
        session_ttl=settings.auth_session_ttl(),
    )
    token = websocket.cookies.get(settings.auth_cookie_name)
    if not token:
        await websocket.send_json(
            _event(
                type_="call.error",
                call_id=call_id,
                sequence=0,
                payload={"code": "session_invalid", "message": "Sign in to continue."},
            )
        )
        await websocket.close(code=4401)
        return
    try:
        account = auth.authenticate(token)
    except SessionInvalid:
        await websocket.send_json(
            _event(
                type_="call.error",
                call_id=call_id,
                sequence=0,
                payload={"code": "session_invalid", "message": "Sign in to continue."},
            )
        )
        await websocket.close(code=4401)
        return

    from apps.api.dependencies import hybrid_retriever

    # Reuse lifespan-built providers — a second Whisper/Piper load OOMs challenge hosts.
    llm = getattr(websocket.app.state, "llm", None) or build_llm_provider(settings)
    stt = getattr(websocket.app.state, "stt", None) or build_stt_provider(settings)
    tts = getattr(websocket.app.state, "tts", None) or build_tts_provider(settings)

    traces = SqliteTraceRepository(database)
    service = CallService(
        calls=SqliteCallRepository(database),
        traces=traces,
        retrieval=hybrid_retriever(settings),
        llm=llm,
    )
    if service.get(account.account_id, call_id) is None:
        await websocket.send_json(
            _event(
                type_="call.error",
                call_id=call_id,
                sequence=0,
                payload={"code": "call_not_found", "message": "Call not found"},
            )
        )
        await websocket.close(code=4404)
        return

    sequence = 0
    active_turn_seq = 0
    pending_speech_end: dict[int, float] = {}
    pending_timing: dict[int, VoiceTurnTimingRecord] = {}
    cancelled_turns: set[int] = set()
    pending_end_after_playback: set[int] = set()
    pending_end_failsafe: dict[int, float] = {}
    pending_end_reason: dict[int, str] = {}
    call_started_mono = time.monotonic()
    last_patient_activity = time.monotonic()
    idle_prompt_sent_at: float | None = None
    max_duration_farewell_sent = False
    idle_hangup_sent = False
    agent_speaking = False
    call_finished = False

    from limen.voice.personas import get_persona

    active_persona_id = service.get_voice_persona(account.account_id, call_id)

    async def emit(type_: str, payload: dict[str, Any]) -> None:
        nonlocal sequence
        sequence += 1
        await websocket.send_json(
            _event(type_=type_, call_id=call_id, sequence=sequence, payload=payload)
        )

    def trace(
        event_type: str,
        *,
        stage: str,
        turn_id: str | None = None,
        detail: str | None = None,
        metrics: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        duration_ms: float | None = None,
        status: str = "ok",
    ) -> None:
        traces.append(
            call_id=call_id,
            account_id=account.account_id,
            stage=stage,
            event_type=event_type,
            turn_id=turn_id,
            label=event_type,
            detail=detail,
            metrics=metrics,
            duration_ms=duration_ms,
            payload=payload or {},
            status=status,
        )

    async def speak_system(
        text: str,
        *,
        end_session: bool,
        call_end_reason: str | None = None,
    ) -> int:
        """TTS a system line (idle / max-duration). Returns turn_seq."""
        nonlocal active_turn_seq, agent_speaking, active_persona_id
        active_turn_seq += 1
        turn_seq = active_turn_seq
        agent_speaking = True
        await emit(
            "call.transcript",
            {
                "turn_id": uuid4().hex,
                "speaker": "agent",
                "text": text,
                "timestamp": datetime.now(tz=UTC).isoformat(),
                "turn_seq": turn_seq,
            },
        )
        await emit("call.state", {"state": "SPEAKING", "turn_seq": turn_seq})
        try:
            audio, tts_timing = await synthesize_with_timing(tts, text, voice=active_persona_id)
        except Exception as error:  # noqa: BLE001
            agent_speaking = False
            await emit(
                "call.error",
                {
                    "code": "tts_failed",
                    "message": f"{type(error).__name__}:{error}",
                    "retryable": True,
                    "assistant_text": text,
                },
            )
            await emit("call.state", {"state": "LISTENING"})
            if end_session:
                await end_voice_session(call_end_reason or "system")
            return turn_seq
        await emit(
            "call.metrics",
            {
                **timing_to_metrics(tts_timing),
                "tts_provider": audio.provider,
                "tts_voice": audio.voice,
                "audio_duration_ms": audio.duration_ms,
                "turn_seq": turn_seq,
                "system_prompt": True,
                "end_session": end_session,
                "call_end_reason": call_end_reason,
            },
        )
        await emit(
            "call.audio",
            {
                "turn_seq": turn_seq,
                "mime_type": audio.mime_type,
                "sample_rate_hz": audio.sample_rate_hz,
            },
        )
        await websocket.send_bytes(audio.audio)
        if end_session:
            pending_end_after_playback.add(turn_seq)
            pending_end_failsafe[turn_seq] = time.monotonic() + _PLAYBACK_END_FAILSAFE_S
            if call_end_reason:
                pending_end_reason[turn_seq] = call_end_reason
        return turn_seq

    async def end_voice_session(reason: str) -> None:
        nonlocal call_finished
        if call_finished:
            service.finish(account_id=account.account_id, call_id=call_id)
            return
        call_finished = True
        service.finish(account_id=account.account_id, call_id=call_id)
        try:
            await emit("call.state", {"state": "ENDED"})
            await emit(
                "call.ended",
                {"reason": reason, "call_end_reason": reason},
            )
        except Exception:  # noqa: BLE001 — socket may already be gone
            pass
        trace(
            "call.ended",
            stage="voice",
            detail=reason,
            payload={"call_end_reason": reason},
        )

    await emit(
        "call.state",
        {
            "state": "LISTENING",
            "voice_persona": active_persona_id,
            "voice_display_name": get_persona(active_persona_id).display_name,
        },
    )

    try:
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive(), timeout=_WS_POLL_S)
            except TimeoutError:
                now = time.monotonic()
                # Failsafe: hang up if playback.completed never arrives.
                for seq, deadline in list(pending_end_failsafe.items()):
                    if now < deadline:
                        continue
                    if seq not in pending_end_after_playback:
                        pending_end_failsafe.pop(seq, None)
                        continue
                    reason = pending_end_reason.pop(seq, "patient_farewell")
                    pending_end_after_playback.discard(seq)
                    pending_end_failsafe.pop(seq, None)
                    await end_voice_session(reason)
                    return
                if agent_speaking:
                    continue
                if now - call_started_mono >= _MAX_CALL_DURATION_S:
                    if not max_duration_farewell_sent and not pending_end_after_playback:
                        max_duration_farewell_sent = True
                        await speak_system(
                            max_duration_farewell(),
                            end_session=True,
                            call_end_reason="max_duration",
                        )
                    continue
                if idle_prompt_sent_at is None:
                    if now - last_patient_activity >= _IDLE_PROMPT_S:
                        await speak_system(
                            idle_check_reply(),
                            end_session=False,
                        )
                        idle_prompt_sent_at = time.monotonic()
                elif (
                    now - idle_prompt_sent_at >= _IDLE_HANGUP_AFTER_PROMPT_S
                    and not idle_hangup_sent
                    and not pending_end_after_playback
                ):
                    idle_hangup_sent = True
                    await speak_system(
                        idle_timeout_farewell(),
                        end_session=True,
                        call_end_reason="idle_prompt_timeout",
                    )
                continue

            if message.get("type") == "websocket.disconnect":
                await end_voice_session("disconnect")
                break

            user_text: str | None = None
            speech_end_mono: float | None = None
            turn_seq = active_turn_seq
            audio_bytes: bytes | None = None

            if message.get("text") is not None:
                raw = message["text"]
                try:
                    body = json.loads(raw)
                except json.JSONDecodeError:
                    body = {"type": "text", "text": raw}
                msg_type = str(body.get("type") or "")
                if msg_type in {"end", "finish"}:
                    await end_voice_session("manual")
                    break
                if msg_type == "voice.select":
                    active_persona_id = service.set_voice_persona(
                        account.account_id,
                        call_id,
                        str(body.get("persona_id") or body.get("voice_persona") or ""),
                    )
                    await emit(
                        "call.state",
                        {
                            "state": "LISTENING",
                            "voice_persona": active_persona_id,
                            "voice_display_name": get_persona(active_persona_id).display_name,
                        },
                    )
                    continue
                if msg_type == "voice.interrupt":
                    cancelled_turns.add(active_turn_seq)
                    agent_speaking = False
                    service.mark_voice_interrupted(account_id=account.account_id, call_id=call_id)
                    trace(
                        "voice.interrupted",
                        stage="voice",
                        detail=f"turn_seq={active_turn_seq}",
                        payload={"turn_seq": active_turn_seq, "reason": "barge_in"},
                    )
                    await emit(
                        "call.state",
                        {"state": "INTERRUPTED", "turn_seq": active_turn_seq},
                    )
                    await emit("call.state", {"state": "LISTENING"})
                    continue
                if msg_type == "voice.playback.started":
                    turn_seq_ack = int(body.get("turn_seq") or 0)
                    started_mono = body.get("agent_audio_started_monotonic")
                    received_mono = body.get("agent_audio_received_monotonic")
                    if isinstance(started_mono, (int, float)):
                        speech_end = pending_speech_end.get(turn_seq_ack)
                        latency = compute_voice_response_latency_ms(
                            speech_end_monotonic=speech_end,
                            agent_audio_started_monotonic=float(started_mono),
                        )
                        record = pending_timing.get(turn_seq_ack)
                        if record is not None:
                            record.audio_playback_start = float(started_mono)
                            if isinstance(received_mono, (int, float)):
                                record.audio_received_browser = float(received_mono)
                            record.validate_invariants()
                            metrics_payload = record.to_metrics()
                            if latency is not None:
                                metrics_payload["voice_response_latency_ms"] = latency
                                metrics_payload["challenge_voice_e2e_ms"] = latency
                            await emit(
                                "call.metrics",
                                {**metrics_payload, "turn_seq": turn_seq_ack},
                            )
                            if latency is not None and not blocking_e2e_reasons(
                                record.invalid_reasons
                            ):
                                _record_voice_sample(
                                    service=service,
                                    account_id=account.account_id,
                                    call_id=call_id,
                                    latency_ms=latency,
                                )
                            trace(
                                "voice.playback.started",
                                stage="voice",
                                metrics=metrics_payload,
                                payload={
                                    "turn_seq": turn_seq_ack,
                                    "valid": record.valid,
                                    "invalid_reasons": record.invalid_reasons,
                                },
                                status="ok" if record.valid else "error",
                            )
                        elif latency is not None:
                            # Legacy path without structured record.
                            _record_voice_sample(
                                service=service,
                                account_id=account.account_id,
                                call_id=call_id,
                                latency_ms=latency,
                            )
                            await emit(
                                "call.metrics",
                                {
                                    "voice_response_latency_ms": latency,
                                    "challenge_voice_e2e_ms": latency,
                                    "turn_seq": turn_seq_ack,
                                },
                            )
                            trace(
                                "voice.playback.started",
                                stage="voice",
                                metrics={"voice_response_latency_ms": latency},
                                payload={"turn_seq": turn_seq_ack},
                            )
                    continue
                if msg_type == "voice.playback.completed":
                    agent_speaking = False
                    done_seq = body.get("turn_seq")
                    try:
                        done_seq_i = int(done_seq) if done_seq is not None else None
                    except (TypeError, ValueError):
                        done_seq_i = None
                    if done_seq_i is not None and done_seq_i in pending_end_after_playback:
                        pending_end_after_playback.discard(done_seq_i)
                        pending_end_failsafe.pop(done_seq_i, None)
                        reason = pending_end_reason.pop(done_seq_i, "patient_farewell")
                        await end_voice_session(reason)
                        break
                    # Open LISTENING only after browser playback ends — emitting
                    # LISTENING right after send_bytes lets speaker echo hit STT.
                    await emit(
                        "call.state",
                        {
                            "state": "LISTENING",
                            "turn_seq": body.get("turn_seq"),
                        },
                    )
                    trace(
                        "voice.playback.completed",
                        stage="voice",
                        payload={"turn_seq": body.get("turn_seq")},
                    )
                    continue
                if msg_type == "voice.mic.requested":
                    trace("voice.mic.requested", stage="voice")
                    continue
                if msg_type == "voice.mic.granted":
                    trace("voice.mic.granted", stage="voice")
                    continue
                if msg_type == "voice.speech.started":
                    last_patient_activity = time.monotonic()
                    idle_prompt_sent_at = None
                    trace("voice.speech.started", stage="voice")
                    continue
                if msg_type == "voice.speech.ended":
                    last_patient_activity = time.monotonic()
                    idle_prompt_sent_at = None
                    speech_end_mono = body.get("speech_end_monotonic")
                    if isinstance(speech_end_mono, (int, float)):
                        # Will attach to next audio frame / text turn.
                        pending_speech_end[active_turn_seq + 1] = float(speech_end_mono)
                    trace(
                        "voice.speech.ended",
                        stage="voice",
                        payload={"speech_end_monotonic": speech_end_mono},
                    )
                    continue
                if msg_type == "voice.audio":
                    # JSON envelope with base64 is not used; prefer binary frames.
                    continue
                user_text = body.get("text") or body.get("transcript")
                if body.get("speech_end_monotonic") is not None:
                    try:
                        speech_end_mono = float(body["speech_end_monotonic"])
                    except (TypeError, ValueError):
                        speech_end_mono = None
                if user_text:
                    last_patient_activity = time.monotonic()
                    idle_prompt_sent_at = None

            elif message.get("bytes") is not None:
                last_patient_activity = time.monotonic()
                idle_prompt_sent_at = None
                audio_bytes = message["bytes"]
                active_turn_seq += 1
                turn_seq = active_turn_seq
                speech_end_mono = pending_speech_end.get(turn_seq)
                if speech_end_mono is None:
                    speech_end_mono = time.perf_counter()
                    pending_speech_end[turn_seq] = speech_end_mono

                await emit(
                    "call.state",
                    {"state": "PROCESSING_STT", "turn_seq": turn_seq},
                )
                trace(
                    "voice.audio.upload.completed",
                    stage="voice",
                    payload={"bytes": len(audio_bytes), "turn_seq": turn_seq},
                )
                trace("stt.started", stage="stt", payload={"turn_seq": turn_seq})
                tmp_wav: Path | None = None
                try:
                    tmp_wav = _write_transient_voice_wav(
                        settings,
                        call_id=call_id,
                        turn_seq=turn_seq,
                        audio=audio_bytes,
                    )
                    transcript, stt_timing = await transcribe_with_timing(
                        stt,
                        audio_bytes,
                        language="es",
                        speech_end_monotonic=speech_end_mono,
                    )
                except AudioFormatError as error:
                    await emit(
                        "call.error",
                        {
                            "code": "stt_audio_format",
                            "message": str(error),
                            "retryable": True,
                        },
                    )
                    await emit("call.state", {"state": "LISTENING"})
                    continue
                except Exception as error:  # noqa: BLE001
                    row = service._calls.get_call_row(account.account_id, call_id)  # noqa: SLF001
                    if row is not None:
                        blob = service._load_call_metrics_blob(row)  # noqa: SLF001
                        blob["stt_errors"] = int(blob.get("stt_errors") or 0) + 1
                        from limen.clinical.state import ClinicalState

                        clinical = ClinicalState.model_validate_json(
                            row["clinical_state_json"] or "{}"
                        )
                        service._calls.update_runtime(  # noqa: SLF001
                            account_id=account.account_id,
                            call_id=call_id,
                            clinical_state=clinical,
                            final_risk=row["final_risk"],
                            escalated=bool(row["escalated"]),
                            metrics=blob,
                        )
                    await emit(
                        "call.error",
                        {
                            "code": "stt_failed",
                            "message": f"{type(error).__name__}:{error}",
                            "retryable": True,
                        },
                    )
                    await emit("call.state", {"state": "LISTENING"})
                    trace(
                        "provider.error",
                        stage="stt",
                        status="error",
                        detail="stt_failed",
                        payload={"turn_seq": turn_seq},
                    )
                    continue
                finally:
                    _cleanup_transient_voice_wav(tmp_wav)

                user_text = transcript.normalized_text or transcript.text
                user_text = normalize_transcript_text(user_text)
                if is_likely_stt_hallucination(
                    user_text,
                    duration_ms=transcript.duration_ms,
                    confidence=transcript.confidence,
                ):
                    await emit(
                        "call.error",
                        {
                            "code": "stt_hallucination",
                            "message": "No se escuchó una frase clara. Intente de nuevo.",
                            "retryable": True,
                        },
                    )
                    await emit("call.state", {"state": "LISTENING"})
                    trace(
                        "voice.false_barge_in",
                        stage="stt",
                        status="error",
                        detail="stt_hallucination_rejected",
                        payload={
                            "turn_seq": turn_seq,
                            "raw_text": transcript.raw_text,
                            "duration_ms": transcript.duration_ms,
                            "confidence": transcript.confidence,
                        },
                    )
                    continue
                timing_rec = VoiceTurnTimingRecord(
                    sample_id=f"{call_id}:{turn_seq}",
                    turn_id=f"pending-{turn_seq}",
                    speech_end=stt_timing.marks.get("speech_end"),
                    stt_start=stt_timing.marks.get("stt_start"),
                    stt_end=stt_timing.marks.get("stt_end"),
                    extras={
                        "stt_provider": transcript.provider,
                        "stt_model": transcript.model,
                        "stt_device": (transcript.usage_metadata or {}).get("actual_device")
                        or (transcript.usage_metadata or {}).get("device"),
                    },
                )
                pending_timing[turn_seq] = timing_rec
                await emit(
                    "call.metrics",
                    {
                        **timing_to_metrics(stt_timing),
                        "stt_provider": transcript.provider,
                        "stt_model": transcript.model,
                        "stt_confidence": transcript.confidence,
                        "stt_ms": timing_rec.stt_ms,
                        "turn_seq": turn_seq,
                    },
                )
                trace(
                    "stt.completed",
                    stage="stt",
                    duration_ms=stt_timing.stt_ms,
                    metrics=timing_to_metrics(stt_timing),
                    payload={
                        "turn_seq": turn_seq,
                        "raw_text": transcript.raw_text,
                        "normalized_text": transcript.normalized_text,
                        "confidence": transcript.confidence,
                    },
                )

            if not user_text or not str(user_text).strip():
                if audio_bytes is not None:
                    await emit(
                        "call.error",
                        {
                            "code": "empty_transcript",
                            "message": "No speech detected. Please try again.",
                            "retryable": True,
                        },
                    )
                    await emit("call.state", {"state": "LISTENING"})
                continue

            if turn_seq == 0:
                active_turn_seq += 1
                turn_seq = active_turn_seq
                if speech_end_mono is not None:
                    pending_speech_end[turn_seq] = speech_end_mono

            if turn_seq in cancelled_turns:
                continue

            await emit("call.state", {"state": "THINKING", "turn_seq": turn_seq})
            patient_turn_id = uuid4().hex
            turn_proc_start = time.perf_counter()
            if turn_seq in pending_timing:
                pending_timing[turn_seq].turn_processing_start = turn_proc_start
                pending_timing[turn_seq].turn_id = patient_turn_id
            await emit(
                "call.transcript",
                {
                    "turn_id": patient_turn_id,
                    "speaker": "patient",
                    "text": user_text,
                    "timestamp": datetime.now(tz=UTC).isoformat(),
                    "turn_seq": turn_seq,
                },
            )
            trace(
                "turn.processing.started",
                stage="response",
                turn_id=patient_turn_id,
                payload={"turn_seq": turn_seq},
            )
            try:
                result = await service.process_text_turn(
                    account_id=account.account_id,
                    call_id=call_id,
                    user_text=str(user_text),
                )
            except ValueError as error:
                await emit(
                    "call.error",
                    {"code": "invalid_call_state", "message": str(error)},
                )
                continue
            turn_proc_end = time.perf_counter()
            if result is None:
                await emit(
                    "call.error",
                    {"code": "call_not_found", "message": "Call not found"},
                )
                break
            if turn_seq in pending_timing:
                pending_timing[turn_seq].turn_processing_end = turn_proc_end
                llm_lat = result.metrics.get("llm_latency_ms")
                if isinstance(llm_lat, (int, float)) and llm_lat > 0:
                    pending_timing[turn_seq].llm_end = turn_proc_end
                    pending_timing[turn_seq].llm_start = turn_proc_end - (float(llm_lat) / 1000.0)

            if turn_seq in cancelled_turns:
                # SafetyDecision already persisted by process_text_turn — skip stale audio.
                await emit(
                    "call.metrics",
                    {
                        "stale_turn_discarded": True,
                        "turn_seq": turn_seq,
                        "turn_id": result.turn_id,
                    },
                )
                await emit("call.state", {"state": "LISTENING"})
                continue

            await emit(
                "call.clinical_state",
                result.clinical_state.model_dump(mode="json"),
            )
            await emit(
                "call.safety",
                {
                    "risk": result.safety.severity.name,
                    "escalate": result.safety.escalate,
                    "reasons": list(result.safety.reasons),
                },
            )
            if result.evidence:
                await emit(
                    "call.evidence",
                    {"chunks": [chunk.model_dump(mode="json") for chunk in result.evidence]},
                )
            metrics_out = dict(result.metrics)
            metrics_out["turn_seq"] = turn_seq
            # clinical_ms = extraction stage only; full core path is turn_processing_ms.
            metrics_out["turn_processing_ms"] = (
                pending_timing[turn_seq].turn_processing_ms
                if turn_seq in pending_timing
                else result.metrics.get("latency_ms")
            )
            if len(result.assistant_text) > 320:
                metrics_out["response_length_anomaly"] = True
            await emit("call.metrics", metrics_out)
            await emit(
                "call.transcript",
                {
                    "turn_id": result.turn_id or result.turn.turn_id,
                    "speaker": "agent",
                    "text": result.assistant_text,
                    "timestamp": datetime.now(tz=UTC).isoformat(),
                    "turn_seq": turn_seq,
                },
            )

            if turn_seq in cancelled_turns:
                await emit("call.state", {"state": "LISTENING"})
                continue

            await emit("call.state", {"state": "SPEAKING", "turn_seq": turn_seq})
            agent_speaking = True
            trace(
                "tts.started",
                stage="tts",
                turn_id=result.turn_id,
                payload={"turn_seq": turn_seq},
            )
            try:
                persona_voice = active_persona_id
                if result.conversation and result.conversation.assistant_persona_id:
                    persona_voice = result.conversation.assistant_persona_id
                    active_persona_id = persona_voice
                audio, tts_timing = await synthesize_with_timing(
                    tts, result.assistant_text, voice=persona_voice
                )
            except Exception as error:  # noqa: BLE001
                agent_speaking = False
                await emit(
                    "call.error",
                    {
                        "code": "tts_failed",
                        "message": f"{type(error).__name__}:{error}",
                        "retryable": not bool(result.metrics.get("end_session")),
                        "assistant_text": result.assistant_text,
                    },
                )
                trace(
                    "provider.error",
                    stage="tts",
                    status="error",
                    detail="tts_failed",
                    payload={"turn_seq": turn_seq},
                )
                # Farewell/wrapup/idle must still hang up even if TTS fails —
                # otherwise the session stays open with no audio to complete.
                if result.metrics.get("end_session"):
                    reason = str(result.metrics.get("call_end_reason") or "patient_farewell")
                    await end_voice_session(reason)
                    break
                await emit("call.state", {"state": "LISTENING"})
                continue

            if turn_seq in pending_timing:
                pending_timing[turn_seq].tts_start = tts_timing.marks.get("tts_start")
                pending_timing[turn_seq].tts_ready = tts_timing.marks.get("tts_end")
                proxy = pending_timing[turn_seq].server_tts_ready_proxy_ms
                tts_timing.extras["SERVER_TTS_READY_PROXY_ms"] = proxy
                pending_timing[turn_seq].validate_invariants()

            if turn_seq in cancelled_turns:
                await emit(
                    "call.metrics",
                    {"stale_tts_discarded": True, "turn_seq": turn_seq},
                )
                await emit("call.state", {"state": "LISTENING"})
                continue

            await emit(
                "call.metrics",
                {
                    **timing_to_metrics(tts_timing),
                    "tts_provider": audio.provider,
                    "tts_voice": audio.voice,
                    "audio_duration_ms": audio.duration_ms,
                    "turn_seq": turn_seq,
                },
            )
            # Hint browser: associate upcoming binary frame with turn_seq.
            await emit(
                "call.audio",
                {
                    "turn_seq": turn_seq,
                    "mime_type": audio.mime_type,
                    "sample_rate_hz": audio.sample_rate_hz,
                },
            )
            await websocket.send_bytes(audio.audio)
            trace(
                "tts.completed",
                stage="tts",
                turn_id=result.turn_id,
                duration_ms=tts_timing.tts_ms,
                payload={"turn_seq": turn_seq},
            )
            # Remain SPEAKING until voice.playback.completed (or interrupt).
            if result.metrics.get("end_session"):
                pending_end_after_playback.add(turn_seq)
                pending_end_failsafe[turn_seq] = time.monotonic() + _PLAYBACK_END_FAILSAFE_S
                reason = str(result.metrics.get("call_end_reason") or "patient_farewell")
                pending_end_reason[turn_seq] = reason
            if result.safety.escalate:
                pending_end_after_playback.add(turn_seq)
                pending_end_failsafe[turn_seq] = time.monotonic() + _PLAYBACK_END_FAILSAFE_S
                pending_end_reason[turn_seq] = "escalation"
    except WebSocketDisconnect:
        await end_voice_session("disconnect")
        return
    except Exception as error:  # noqa: BLE001
        await emit(
            "call.error",
            {"code": "voice_session_error", "message": f"{type(error).__name__}:{error}"},
        )
        await websocket.close(code=1011)
