"""Explicit clinical certainty states — unknown is first-class."""

from enum import StrEnum


class ClinicalCertainty(StrEnum):
    """Never coerce missing information into False, 0, or 'normal'."""

    KNOWN_NORMAL = "KNOWN_NORMAL"
    KNOWN_ABNORMAL = "KNOWN_ABNORMAL"
    UNKNOWN = "UNKNOWN"
    CONFLICTING = "CONFLICTING"
