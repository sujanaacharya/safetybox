"""Small in-process audit recording primitives for M3."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from safetybox.events import EventType, SafetyBoxEvent
from safetybox.models import ActionRequest, Decision
from safetybox.protocols import AuditSink


@dataclass(slots=True)
class InMemoryAuditSink:
    """Test-oriented sink whose snapshots cannot mutate its event collection."""

    _events: list[SafetyBoxEvent] = field(default_factory=list, init=False, repr=False)

    def record(self, event: SafetyBoxEvent) -> None:
        self._events.append(event)

    def events(self) -> tuple[SafetyBoxEvent, ...]:
        """Return an immutable snapshot in record order."""
        return tuple(self._events)


@dataclass(slots=True)
class AuditRecorder:
    """Owns session-local sequencing, event construction, and sink delivery.

    This implementation is single-process and not safe for concurrent writers.
    A sequence is committed only after the sink accepts its event, so a failed
    pre-execution write cannot consume a number or permit execution.
    """

    sink: AuditSink
    _last_sequence_by_session: dict[str, int] = field(default_factory=dict, init=False)

    def last_sequence_number(self, session_id: str) -> int:
        """Return the last committed sequence for one session, or zero."""
        return self._last_sequence_by_session.get(session_id, 0)

    def emit(
        self,
        request: ActionRequest,
        event_type: EventType,
        *,
        correlation_id: str,
        parent_event_id: str | None = None,
        rule_id: str | None = None,
        decision: Decision | None = None,
        executed: bool | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> SafetyBoxEvent:
        """Create and deliver a session-ordered event, returning it on success."""
        sequence_number = self._last_sequence_by_session.get(request.session_id, 0) + 1
        event = SafetyBoxEvent(
            event_id=str(uuid4()),
            session_id=request.session_id,
            task_id=request.task_id,
            sequence_number=sequence_number,
            event_type=event_type,
            request_id=request.request_id,
            actor=request.actor,
            action=request.action,
            resource=request.resource,
            correlation_id=correlation_id,
            timestamp=datetime.now(UTC),
            parent_event_id=parent_event_id,
            rule_id=rule_id,
            decision=decision,
            executed=executed,
            metadata={} if metadata is None else metadata,
        )
        self.sink.record(event)
        self._last_sequence_by_session[request.session_id] = sequence_number
        return event
