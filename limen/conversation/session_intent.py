"""Lightweight session intents (farewell / address) — not clinical authority."""

from __future__ import annotations

import re
import unicodedata

_FAREWELL_RE = re.compile(
    r"\b("
    r"adi[oó]s|hasta\s+luego|hasta\s+pronto|me\s+voy|ya\s+me\s+retiro|"
    r"finalizamos|terminamos|cerramos|colgar|cuelga|cuelgue|"
    r"corta\s+la\s+llamada|fin\s+de\s+la\s+llamada|"
    r"(?:finalizar?|terminar?|cerrar?)\s+(?:la\s+)?"
    r"(?:llamada|reuni[oó]n|sesi[oó]n|consulta|conversaci[oó]n)|"
    r"quiero\s+(?:terminar|finalizar|cerrar)\b|"
    r"eso\s+es\s+todo|por\s+ahora\s+(?:es\s+todo|nada\s+m[aá]s)|"
    r"no\s+(?:necesito|quiero)\s+nada\s+m[aá]s|"
    r"nada\s+m[aá]s|ya\s+est[aá]|chao|nos\s+vemos"
    r")\b",
    re.IGNORECASE,
)

_WRAPUP_RE = re.compile(
    r"\b("
    r"estoy\s+bien|me\s+siento\s+bien|todo\s+bien|"
    r"no\s+tengo\s+(?:m[aá]s\s+)?(?:dudas|preguntas)|"
    r"eso\s+era\s+todo|por\s+mi\s+parte\s+(?:es\s+)?todo|"
    r"no\s+hay\s+nada\s+m[aá]s|gracias\s+(?:eso\s+es\s+todo|por\s+ahora)"
    r")\b",
    re.IGNORECASE,
)

# Patient greets / addresses the live assistant persona by name.
_ASSISTANT_ADDRESS_RE = re.compile(
    r"(?:"
    r"\b(?:hola|buenas|buen\s+d[ií]a|buenos\s+d[ií]as|"
    r"buenas\s+(?:tardes|noches)|muy\s+buenas|"
    r"o[ií]game|disculpe|por\s+favor)\b"
    r".{0,24}?"
    r"\b(elena|anikka|anika|nikolas|nicolas|alex|limen)\b"
    r"|"
    r"\b(elena|anikka|anika|nikolas|nicolas|alex|limen)\b"
    r"\s*[,.!?]?\s*$"
    r")",
    re.IGNORECASE | re.DOTALL,
)

_GREETING_RE = re.compile(
    r"\b("
    r"hola|buenas|buen\s+d[ií]a|buenos\s+d[ií]as|"
    r"buenas\s+(tardes|noches)|muy\s+buenas|"
    r"qu[eé]\s+tal|c[oó]mo\s+est[aá]"
    r")\b",
    re.IGNORECASE,
)

_CLINICAL_HINT_RE = re.compile(
    r"\b("
    r"dolor|duele|herida|fiebre|sangre|sangrad|n[aá]useas|"
    r"respir|ahogo|operaci|cirug|medicament|pastilla|"
    r"empeor|mejor|inflam|pus|supura"
    r")\b",
    re.IGNORECASE,
)

_GENERIC_ALIASES = frozenset(
    {
        "",
        "paciente",
        "patient",
        "user",
        "usuario",
        "demo",
        "limen",
        "doctor",
        "doctora",
        "enfermera",
        "enfermero",
        # Assistant personas must never become the patient name.
        "elena",
        "anikka",
        "anika",
        "nikolas",
        "nicolas",
        "alex",
    }
)

_ASSISTANT_NAME_FOLDED = frozenset(
    {"elena", "anikka", "anika", "nikolas", "nicolas", "alex", "limen"}
)

_EVERYDAY_PHATIC_RE = re.compile(
    r"\b("
    r"sue[nñ]o|cansad[oa]|aburrid[oa]|feliz|triste|"
    r"bien|mal|regular|asi\s+asi|más\s+o\s+menos|"
    r"gracias|ok|okay|vale|de\s+acuerdo"
    r")\b",
    re.IGNORECASE,
)

# Tokens that look like names but are clinical / filler speech.
_NAME_BLOCKLIST = frozenset(
    {
        "dolor",
        "herida",
        "fiebre",
        "sangre",
        "sangrado",
        "mejor",
        "peor",
        "bien",
        "mal",
        "aqui",
        "aquí",
        "alla",
        "allá",
        "ahora",
        "luego",
        "gracias",
        "hola",
        "adios",
        "adiós",
        "ok",
        "okay",
        "paciente",
        "hombre",
        "mujer",
        "señor",
        "senor",
        "señora",
        "senora",
        "usted",
    }
)

_NAME_CAPTURE_RE = re.compile(
    r"(?:"
    r"me\s+llam[oaó]\s+"
    r"|mi\s+nombre\s+es\s+"
    r"|pueden\s+decirme\s+"
    r"|me\s+pueden\s+decir\s+"
    r"|prefiero\s+que\s+me\s+diga(?:n)?\s+"
    r"|\bsoy\s+"
    r")"
    r"([A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{2,24})"
    r"(?:\s+[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{2,24})?",
    re.IGNORECASE,
)

_ASK_PREFERRED_NAME_RE = re.compile(
    r"(?:"
    r"c[oó]mo\s+prefiere\s+que\s+le\s+(?:diga|llame)"
    r"|c[oó]mo\s+se\s+llama"
    r"|cu[aá]l\s+es\s+su\s+nombre"
    r"|me\s+dice\s+su\s+nombre"
    r"|c[oó]mo\s+le\s+gustar[ií]a\s+que\s+le\s+(?:diga|llame)"
    r")",
    re.IGNORECASE,
)


def _fold(text: str) -> str:
    raw = unicodedata.normalize("NFKD", (text or "").strip())
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
    return " ".join(raw.casefold().split())


def looks_like_farewell(text: str) -> bool:
    """True when the patient is closing the conversation for now."""
    return _FAREWELL_RE.search(_fold(text)) is not None


def looks_like_wrapup(text: str) -> bool:
    """True when the patient signals they are done without a hard hang-up verb."""
    raw = (text or "").strip()
    if not raw or len(raw) > 120:
        return False
    if looks_like_farewell(raw):
        return False
    if _CLINICAL_HINT_RE.search(raw) and not _WRAPUP_RE.search(_fold(raw)):
        return False
    return _WRAPUP_RE.search(_fold(raw)) is not None


def addresses_assistant_by_name(
    text: str,
    *,
    assistant_name: str | None = None,
) -> bool:
    """True when the patient is speaking *to* the assistant persona by name."""
    raw = (text or "").strip()
    if not raw or len(raw) > 120:
        return False
    if _CLINICAL_HINT_RE.search(raw):
        return False
    folded = _fold(raw)
    if _ASSISTANT_ADDRESS_RE.search(folded):
        return True
    # Short utterance that only greets/names the assistant.
    return bool(
        assistant_name
        and _fold(assistant_name) in folded
        and (_GREETING_RE.search(folded) or len(folded.split()) <= 4)
    )


def looks_like_greeting_only(text: str) -> bool:
    """True for short phatic openings without clinical content."""
    raw = (text or "").strip()
    if not raw or len(raw) > 96:
        return False
    if _CLINICAL_HINT_RE.search(raw):
        return False
    if looks_like_farewell(raw):
        return False
    if addresses_assistant_by_name(raw):
        return True
    return _GREETING_RE.search(_fold(raw)) is not None


def is_assistant_persona_name(name: str | None) -> bool:
    """True when a candidate name is an assistant persona, not a patient."""
    if not name:
        return False
    return _fold(name) in _ASSISTANT_NAME_FOLDED


def patient_display_name_safe(
    candidate: str | None,
    *,
    assistant_name: str | None = None,
) -> str | None:
    """Speakable patient name, never an assistant persona label."""
    cleaned = display_name_for_speech(candidate)
    if cleaned is None:
        return None
    if is_assistant_persona_name(cleaned):
        return None
    if assistant_name and _fold(cleaned) == _fold(assistant_name):
        return None
    return cleaned


def greeting_time_of_day(text: str) -> str:
    """Pick salutation from patient phrasing; default tardes for voice demos."""
    folded = _fold(text)
    if "buen dia" in folded or "buenos dias" in folded or "buen día" in folded:
        return "Buenos días"
    if "buenas noches" in folded or "buena noche" in folded:
        return "Buenas noches"
    if "buenas tardes" in folded or "buena tarde" in folded:
        return "Buenas tardes"
    return "Buenas tardes"


def looks_like_everyday_phatic(text: str) -> bool:
    """Short non-clinical chit-chat (fatigue, thanks) — not a status report."""
    raw = (text or "").strip()
    if not raw or len(raw) > 80:
        return False
    if _CLINICAL_HINT_RE.search(raw):
        return False
    if looks_like_farewell(raw) or looks_like_greeting_only(raw):
        return False
    return _EVERYDAY_PHATIC_RE.search(_fold(raw)) is not None


def everyday_phatic_reply(*, assistant_name: str | None = None) -> str:
    """Brief human ack, then gently return to clinical follow-up."""
    _ = assistant_name  # reserved for future light branding
    return (
        "Claro, muchas gracias por contármelo. El cansancio es frecuente "
        "en la recuperación. ¿Hay algo que le preocupe de su evolución hoy, "
        "como dolor, fiebre o la herida?"
    )


def opening_reply(
    *,
    assistant_name: str | None = None,
    gender: str | None = None,
    display_name: str | None = None,
    user_text: str | None = None,
) -> str:
    """Warm first-turn greeting — never a clinical GREEN boilerplate."""
    name = (assistant_name or "LIMEN").strip() or "LIMEN"
    glad = "encantada" if (gender or "female") == "female" else "encantado"
    safe_patient = patient_display_name_safe(display_name, assistant_name=name)
    who = f", señor {safe_patient}" if safe_patient else ""
    hello = greeting_time_of_day(user_text or "")
    return (
        f"{hello}{who}. Soy {name}, de LIMEN. "
        f"Estoy {glad} de acompañarle en su seguimiento postoperatorio. "
        "¿Cómo se siente en este momento?"
    )


def short_greeting_ack(*, assistant_name: str | None = None) -> str:
    """Brief ack when the patient greets again mid-call."""
    name = (assistant_name or "").strip()
    who = f" Soy {name}." if name else ""
    return f"Hola, aquí sigo.{who} Dígame, ¿cómo se siente ahora?"


def display_name_for_speech(alias: str | None) -> str | None:
    """Return a speakable name, or None when only a generic placeholder exists."""
    if alias is None:
        return None
    cleaned = " ".join(str(alias).strip().split())
    if not cleaned:
        return None
    if cleaned.casefold() in _GENERIC_ALIASES:
        return None
    if is_assistant_persona_name(cleaned):
        return None
    return cleaned


def _title_name(raw: str) -> str:
    parts = [p for p in raw.strip().split() if p]
    return " ".join(p[:1].upper() + p[1:].lower() for p in parts)


def extract_preferred_name(text: str) -> str | None:
    """Pull a preferred given name from speech — presentation only, not clinical truth."""
    if not text or not text.strip():
        return None
    match = _NAME_CAPTURE_RE.search(text.strip())
    if not match:
        return None
    candidate = _title_name(match.group(1))
    folded = candidate.casefold()
    if folded in _GENERIC_ALIASES or folded in _NAME_BLOCKLIST:
        return None
    if is_assistant_persona_name(candidate):
        return None
    if len(candidate) < 2 or len(candidate) > 40:
        return None
    # Reject all-lowercase clinical phrases accidentally captured.
    if any(ch.isdigit() for ch in candidate):
        return None
    return candidate


def assistant_asked_preferred_name(text: str) -> bool:
    """True when the assistant asked how the patient prefers to be addressed."""
    return _ASK_PREFERRED_NAME_RE.search(text or "") is not None


def farewell_reply(*, display_name: str | None = None) -> str:
    safe = patient_display_name_safe(display_name)
    who = f", señor {safe}" if safe else ""
    return (
        f"Entendido{who}. Gracias por conversar. "
        "Recuerde avisar a su equipo de salud si nota empeoramiento "
        "(fiebre alta, dolor fuerte nuevo, sangrado o dificultad para respirar). "
        "Cerramos la llamada por ahora. Hasta pronto."
    )


def wrapup_reply(*, display_name: str | None = None) -> str:
    """Short clinical wrap-up then hang up — no fake booking offers."""
    safe = patient_display_name_safe(display_name)
    who = f", señor {safe}" if safe else ""
    return (
        f"Perfecto{who}. Antes de cerrar: observe dolor, fiebre y la herida; "
        "si empeora, contacte a su equipo de salud. "
        "Gracias por su tiempo. Hasta pronto."
    )


def idle_check_reply() -> str:
    """Single presence check before idle hang-up."""
    return "¿Sigue ahí? Si no necesita nada más por ahora, cerramos la llamada en un momento."


def idle_timeout_farewell() -> str:
    """Final line when the patient does not answer the idle check."""
    return (
        "No he escuchado respuesta, así que cierro por ahora. "
        "Si nota empeoramiento, contacte a su equipo de salud. Hasta pronto."
    )


def max_duration_farewell() -> str:
    """Hard cap hang-up for cost and session hygiene."""
    return (
        "Hemos alcanzado el tiempo máximo de esta llamada. "
        "Si necesita seguimiento, inicie una nueva. "
        "Recuerde avisar a su equipo ante empeoramiento. Hasta pronto."
    )
