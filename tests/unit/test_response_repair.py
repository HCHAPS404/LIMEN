"""Response repair: truncated drafts and identity phrasing."""

from __future__ import annotations

from limen.conversation.response_repair import (
    looks_truncated_draft,
    repair_identity_phrasing,
    trim_to_last_complete_sentence,
)
from limen.conversation.response_validator import validate_patient_response
from limen.safety.decision import SafetyDecision
from limen.voice.speech_text import prepare_speech_text
from limen.voice.transcript_repair import repair_transcript_text


def test_detects_significativs_truncation() -> None:
    bad = (
        "Entiendo que tu dolor ha disminuido significativs"
    )
    assert looks_truncated_draft(bad)
    assert trim_to_last_complete_sentence(
        "El dolor bajó. Luego significativs"
    ) == "El dolor bajó."


def test_validator_rejects_truncated_and_informal() -> None:
    safety = SafetyDecision.green("generative_default")
    truncated = validate_patient_response(
        "Su dolor bajó significativs",
        safety=safety,
    )
    assert not truncated.ok
    assert "truncated_or_broken_word" in truncated.reasons

    informal = validate_patient_response(
        "Entiendo que tu dolor bajó. ¿Puedes contarme más?",
        safety=safety,
    )
    assert not informal.ok
    assert "informal_tu_address" in informal.reasons

    booking = validate_patient_response(
        "¿Le gustaría ayuda para programar una cita?",
        safety=safety,
    )
    assert not booking.ok
    assert "unsupported_booking_or_callback_offer" in booking.reasons


def test_repair_estoy_name() -> None:
    assert "Soy Anikka" in repair_identity_phrasing("Estoy Anikka, aquí para apoyar.")


def test_transcript_repairs_colombian_clinical_mishearings() -> None:
    fixed = repair_transcript_text(
        "me cuesta moverme boletas y tengo somareos y valores de cabeza"
    )
    assert "muletas" in fixed
    assert "mareos" in fixed
    assert "dolores de cabeza" in fixed


def test_speech_text_softens_long_adverbs() -> None:
    out = prepare_speech_text("Bajó significativamente el dolor")
    assert "significativamente" not in out.casefold()
    assert "notable" in out.casefold()
