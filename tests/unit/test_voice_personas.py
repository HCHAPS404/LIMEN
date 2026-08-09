"""Voice persona catalog and resolution."""

from __future__ import annotations

from limen.voice.personas import (
    DEFAULT_PERSONA_ID,
    get_persona,
    list_personas,
    normalize_persona_id,
)


def test_default_is_elena() -> None:
    assert DEFAULT_PERSONA_ID == "elena"
    assert get_persona(None).display_name == "Elena"
    assert get_persona(None).gender == "female"


def test_four_personas() -> None:
    ids = {p.id for p in list_personas()}
    assert ids == {"elena", "nikolas", "anikka", "alex"}
    assert get_persona("nikolas").gender == "male"
    assert get_persona("anikka").piper_voice == "es_MX-claude-high"
    assert get_persona("anikka").length_scale >= 1.10
    assert "latinoamericano" in get_persona("anikka").blurb_es.casefold()
    assert get_persona("elena").piper_voice == "es_ES-sharvard-medium"
    assert get_persona("elena").speaker_id == 1
    assert get_persona("alex").piper_voice == "es_ES-sharvard-medium"
    assert get_persona("alex").speaker_id == 0


def test_normalize_unknown_falls_back() -> None:
    assert normalize_persona_id("unknown") == "elena"
    assert normalize_persona_id("NIKOLAS") == "nikolas"
