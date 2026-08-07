"""Decision timeline — Planned beyond foundation."""

from limen.tracing.events import TraceEvent


def sort_timeline(events: list[TraceEvent]) -> list[TraceEvent]:
    return sorted(events, key=lambda e: e.timestamp)
