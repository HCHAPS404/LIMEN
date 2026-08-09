"""Assistant voice personas — presentation only (not clinical authority).

Each persona maps to a Piper voicepack. Chat text only inherits grammatical gender
and the display name; safety/RAG are unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

GrammaticalGender = Literal["female", "male"]
PersonaId = Literal["elena", "nikolas", "anikka", "alex"]

DEFAULT_PERSONA_ID: PersonaId = "elena"


@dataclass(frozen=True, slots=True)
class VoicePersona:
    """User-facing assistant voice identity."""

    id: PersonaId
    display_name: str
    gender: GrammaticalGender
    """Piper voice file stem, e.g. es_MX-claude-high."""
    piper_voice: str
    """Optional multi-speaker id inside the onnx (sharvard M/F)."""
    speaker_id: int | None = None
    """Short operator hint (not shown as clinical data)."""
    blurb_es: str = ""
    huggingface_subdir: str = ""
    """Prosody knobs — Piper cannot invent age; we bias tempo/variation.
    length_scale > 1.0 = slower speech.
    """
    length_scale: float = 1.08
    noise_scale: float = 0.667
    noise_w_scale: float = 0.80
    """Silence between Piper sentence chunks (ms) — longer = less rushed."""
    sentence_silence_ms: float = 160.0


# Official rhasspy/piper-voices. Age is a product persona, not model metadata.
# Anikka uses es_MX (LatAm) — Piper has no es_CO pack; MX is closer to
# Colombian Spanish than rioplatense Daniela. Elena/Alex: sharvard F/M.
VOICE_PERSONAS: dict[PersonaId, VoicePersona] = {
    "elena": VoicePersona(
        id="elena",
        display_name="Elena",
        gender="female",
        piper_voice="es_ES-sharvard-medium",
        speaker_id=1,  # F
        blurb_es="Señora — voz femenina más natural (Sharvard F).",
        huggingface_subdir="es/es_ES/sharvard/medium",
        length_scale=1.14,
        noise_scale=0.667,
        noise_w_scale=0.82,
        sentence_silence_ms=200.0,
    ),
    "nikolas": VoicePersona(
        id="nikolas",
        display_name="Nikolas",
        gender="male",
        piper_voice="es_ES-davefx-medium",
        blurb_es="Señor — español de España.",
        huggingface_subdir="es/es_ES/davefx/medium",
        length_scale=1.08,
        noise_scale=0.667,
        noise_w_scale=0.82,
        sentence_silence_ms=170.0,
    ),
    "anikka": VoicePersona(
        id="anikka",
        display_name="Anikka",
        gender="female",
        piper_voice="es_MX-claude-high",
        blurb_es="Joven adulta (~25) — español latinoamericano.",
        huggingface_subdir="es/es_MX/claude/high",
        length_scale=1.12,
        noise_scale=0.667,
        noise_w_scale=0.82,
        sentence_silence_ms=185.0,
    ),
    "alex": VoicePersona(
        id="alex",
        display_name="Alex",
        gender="male",
        piper_voice="es_ES-sharvard-medium",
        speaker_id=0,  # M
        blurb_es="Joven adulto (~26) — voz masculina más natural (Sharvard M).",
        huggingface_subdir="es/es_ES/sharvard/medium",
        length_scale=1.10,
        noise_scale=0.667,
        noise_w_scale=0.82,
        sentence_silence_ms=190.0,
    ),
}


def normalize_persona_id(raw: str | None) -> PersonaId:
    key = (raw or "").strip().casefold()
    for persona_id in VOICE_PERSONAS:
        if persona_id == key:
            return persona_id
    return DEFAULT_PERSONA_ID


def get_persona(persona_id: str | None) -> VoicePersona:
    return VOICE_PERSONAS[normalize_persona_id(persona_id)]


def list_personas() -> list[VoicePersona]:
    return [VOICE_PERSONAS[k] for k in ("elena", "nikolas", "anikka", "alex")]
