"""Canonical immutable M3 events for reference-monitor execution."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType

from safetybox.models import Decision


def _freeze(value: object) -> object:
    """Make supported metadata containers recursively immutable."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set | frozenset):
        return frozenset(_freeze(item) for item in value)
    return value


class EventType(StrEnum):
    """The deliberately small M3 ReferenceMonitor lifecycle registry."""

    ADAPTER_REQUEST_RECEIVED = "ADAPTER_REQUEST_RECEIVED"
    CANONICALIZATION_STARTED = "CANONICALIZATION_STARTED"
    CANONICALIZATION_SUCCEEDED = "CANONICALIZATION_SUCCEEDED"
    CANONICALIZATION_FAILED = "CANONICALIZATION_FAILED"
    ACTION_REQUESTED = "ACTION_REQUESTED"
    AUTHORIZATION_STARTED = "AUTHORIZATION_STARTED"
    AUTHORIZATION_ALLOWED = "AUTHORIZATION_ALLOWED"
    AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"
    AUTHORIZATION_FAILED = "AUTHORIZATION_FAILED"
    TARGET_VALIDATION_STARTED = "TARGET_VALIDATION_STARTED"
    TARGET_VALIDATION_SUCCEEDED = "TARGET_VALIDATION_SUCCEEDED"
    TARGET_VALIDATION_FAILED = "TARGET_VALIDATION_FAILED"
    EXECUTION_STARTED = "EXECUTION_STARTED"
    EXECUTION_SUCCEEDED = "EXECUTION_SUCCEEDED"
    EXECUTION_FAILED = "EXECUTION_FAILED"


@dataclass(frozen=True, slots=True)
class SafetyBoxEvent:
    """One committed, attributable observation in a session-local trace.

    ``sequence_number`` is the authoritative ordering mechanism. ``timestamp``
    is UTC observational metadata only and must not be used to order events.
    ``metadata`` intentionally excludes raw request arguments and tool results.
    """

    event_id: str
    session_id: str
    task_id: str
    sequence_number: int
    event_type: EventType
    request_id: str
    actor: str
    action: str
    resource: str
    correlation_id: str
    timestamp: datetime
    rule_id: str | None = None
    decision: Decision | None = None
    executed: bool | None = None
    parent_event_id: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.sequence_number < 1:
            raise ValueError("Event sequence_number must be positive.")
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("Event timestamp must be timezone-aware.")
        frozen_metadata = _freeze(self.metadata)
        if not isinstance(frozen_metadata, Mapping):  # pragma: no cover - type invariant
            raise TypeError("Event metadata must be a mapping.")
        object.__setattr__(self, "metadata", frozen_metadata)
