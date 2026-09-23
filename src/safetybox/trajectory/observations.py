"""Deterministic derivation of M5 observations from canonical M3 events."""

from __future__ import annotations

from safetybox.events import EventType, SafetyBoxEvent
from safetybox.models import Decision
from safetybox.trajectory.models import CompletedActionObservation


class ActionObservationBuilder:
    """Derive terminal action outcomes without duplicating canonical evidence."""

    def build(self, event: SafetyBoxEvent) -> CompletedActionObservation | None:
        """Return an observation for the M5-relevant terminal event, if any."""
        if event.event_type is EventType.EXECUTION_SUCCEEDED:
            expected_decision, expected_executed = Decision.ALLOW, True
        elif event.event_type is EventType.AUTHORIZATION_DENIED:
            expected_decision, expected_executed = Decision.DENY, False
        else:
            return None
        if event.decision is not expected_decision or event.executed is not expected_executed:
            raise ValueError("Terminal M3 event has inconsistent decision or execution semantics.")
        return CompletedActionObservation(
            session_id=event.session_id,
            task_id=event.task_id,
            request_id=event.request_id,
            actor=event.actor,
            action=event.action,
            resource=event.resource,
            policy_decision=event.decision,
            executed=event.executed,
            sequence_number=event.sequence_number,
            canonical_event_id=event.event_id,
        )
