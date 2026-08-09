"""Session intents: farewell, display name, preferred-name capture."""

from __future__ import annotations

from limen.conversation.session_intent import (
    assistant_asked_preferred_name,
    display_name_for_speech,
    extract_preferred_name,
    farewell_reply,
    looks_like_farewell,
    looks_like_greeting_only,
    opening_reply,
    short_greeting_ack,
)


def test_farewell_phrases() -> None:
    assert looks_like_farewell("me voy")
    assert looks_like_farewell("Adiós, gracias")
    assert looks_like_farewell("finalizamos por el momento")
    assert looks_like_farewell("Quiero terminar la reunión")
    assert looks_like_farewell("quiero finalizar la sesión")
    assert looks_like_farewell("cerrar la consulta")
    assert not looks_like_farewell("me duele la herida")


def test_display_name_skips_generic() -> None:
    assert display_name_for_speech("Paciente") is None
    assert display_name_for_speech("María") == "María"


def test_farewell_reply_optional_name() -> None:
    text = farewell_reply(display_name="María")
    assert "señor María" in text
    assert "Hasta pronto" in farewell_reply(display_name=None)


def test_extract_preferred_name() -> None:
    assert extract_preferred_name("ok me llamo Juan") == "Juan"
    assert extract_preferred_name("me llamó Juan") == "Juan"
    assert extract_preferred_name("soy Ana") == "Ana"
    assert extract_preferred_name("mi nombre es Carlos") == "Carlos"
    assert extract_preferred_name("me duele la herida") is None
    assert extract_preferred_name("soy paciente") is None
    assert extract_preferred_name("soy dolor") is None


def test_assistant_asked_preferred_name() -> None:
    assert assistant_asked_preferred_name(
        "Para continuar, ¿cómo prefiere que le diga?"
    )
    assert not assistant_asked_preferred_name("¿Cómo se ve la herida?")


def test_greeting_only_phrases() -> None:
    assert looks_like_greeting_only("Muy buenas tardes.")
    assert looks_like_greeting_only("Hola, buenas tardes!")
    assert looks_like_greeting_only("Buenos días")
    assert not looks_like_greeting_only("Muy buenas tardes, me duele la herida")
    assert not looks_like_greeting_only("Adiós")


def test_opening_reply_is_not_clinical_boilerplate() -> None:
    text = opening_reply(assistant_name="Anikka", gender="female")
    assert "Anikka" in text
    assert "recuperación esperada" not in text
    assert "documentación adicional" not in text
    assert "¿Cómo se siente" in text
    assert "Soy Anikka" in text


def test_greeting_time_matches_patient() -> None:
    from limen.conversation.session_intent import greeting_time_of_day, opening_reply

    assert greeting_time_of_day("Hola, muy buenas tardes.") == "Buenas tardes"
    text = opening_reply(
        assistant_name="Anikka",
        gender="female",
        display_name="Anikka",  # must be ignored — assistant ≠ patient
        user_text="Hola, muy buenas tardes.",
    )
    assert "Buenas tardes" in text
    assert "señor Anikka" not in text
    assert "Soy Anikka" in text


def test_display_name_rejects_assistant_personas() -> None:
    assert display_name_for_speech("Anikka") is None
    assert display_name_for_speech("Elena") is None
    assert extract_preferred_name("me llamo Anikka") is None
    assert "Dígame" in short_greeting_ack(assistant_name="Anikka")
    assert looks_like_greeting_only("Hola Anika, ¿cómo estás?")
    assert looks_like_farewell("quiero finalizar la llamada")


def test_addresses_assistant_hola_anika() -> None:
    from limen.conversation.session_intent import addresses_assistant_by_name

    assert addresses_assistant_by_name("Hola, Anika.")
    assert addresses_assistant_by_name("Hola Anikka", assistant_name="Anikka")
    assert looks_like_greeting_only("Hola, Anika.")


def test_wrapup_phrases() -> None:
    from limen.conversation.session_intent import looks_like_wrapup, wrapup_reply

    assert looks_like_wrapup("estoy bien, gracias")
    assert looks_like_wrapup("eso era todo")
    assert not looks_like_wrapup("me duele la herida")
    assert "Hasta pronto" in wrapup_reply()
