"""Style validator: reject third-person narration of the patient."""

from __future__ import annotations

from limen.conversation.response_validator import validate_patient_response
from limen.safety.decision import SafetyDecision


def test_rejects_third_person_patient_narration() -> None:
    safety = SafetyDecision.green("generative_default")
    bad = "Entiendo que Juan ha agradecido nuestra ayuda. Estoy aquí para apoyarlo."
    result = validate_patient_response(bad, safety=safety, patient_display_name="Juan")
    assert not result.ok
    assert "third_person_patient_narration" in result.reasons


def test_accepts_second_person_with_name() -> None:
    safety = SafetyDecision.green("generative_default")
    good = "Gracias por comunicarse, señor Juan. Cuénteme cómo se siente la herida hoy."
    result = validate_patient_response(good, safety=safety, patient_display_name="Juan")
    assert result.ok


def test_rejects_invented_name_when_session_has_none() -> None:
    safety = SafetyDecision.green("generative_default")
    leaked = "Muy buenas tardes señor/señora Juan. Es un placer escucharlo hoy. ¿Cómo se siente?"
    result = validate_patient_response(leaked, safety=safety, patient_display_name=None)
    assert not result.ok
    assert "invented_or_stale_patient_name" in result.reasons


def test_rejects_assistant_name_as_patient_vocative() -> None:
    safety = SafetyDecision.green("generative_default")
    bad = "Gracias por contactarnos en esta mañana, Anikka. Estoy aquí para apoyarle."
    result = validate_patient_response(
        bad,
        safety=safety,
        patient_display_name=None,
        assistant_display_name="Anikka",
    )
    assert not result.ok
    assert "assistant_name_used_as_patient" in result.reasons


def test_accepts_greeting_without_name() -> None:
    safety = SafetyDecision.green("generative_default")
    good = "Buenos días. Soy LIMEN. ¿Cómo se siente en este momento de su recuperación?"
    result = validate_patient_response(good, safety=safety, patient_display_name=None)
    assert result.ok
