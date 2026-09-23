"""Bounded, ordered, observational trajectory monitoring for M5."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from safetybox.events import SafetyBoxEvent
from safetybox.trajectory.models import (
    CompletedActionObservation,
    TrajectoryEvaluation,
    TrajectoryFinding,
)
from safetybox.trajectory.observations import ActionObservationBuilder
from safetybox.trajectory.rules import (
    RepeatedDeniedBoundaryProbingRule,
    StagedCollectionToEgressRule,
    TrajectoryRule,
)


class TrajectoryOrderingError(ValueError):
    """Canonical events were not supplied in strict per-session sequence order."""


@dataclass(slots=True)
class TrajectoryMonitor:
    """Evaluate configured rules over bounded, session-and-task-local observations.

    Events are accepted only in increasing order for each session. Gaps are
    accepted because M5 can observe a filtered delivery stream, but they remain
    visible in finding ranges. No event is reordered. This monitor is strictly
    observational: it does not call tools, authorize requests, or modify task
    contracts/capabilities.
    """

    window_size: int = 8
    rules: tuple[TrajectoryRule, ...] = field(
        default_factory=lambda: (
            StagedCollectionToEgressRule(),
            RepeatedDeniedBoundaryProbingRule(),
        )
    )
    _builder: ActionObservationBuilder = field(default_factory=ActionObservationBuilder, init=False)
    _last_sequence_by_session: dict[str, int] = field(default_factory=dict, init=False)
    _histories: dict[tuple[str, str], deque[CompletedActionObservation]] = field(
        default_factory=dict, init=False
    )
    _findings_by_session: dict[str, list[TrajectoryFinding]] = field(
        default_factory=dict, init=False
    )
    _deduplication_keys: set[tuple[str, str, tuple[str, ...]]] = field(
        default_factory=set, init=False
    )
    _processed_event_counts: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        if self.window_size < 1:
            raise ValueError("Trajectory window_size must be positive.")
        if not self.rules:
            raise ValueError("Trajectory monitor requires at least one rule.")
        rule_ids = tuple(rule.rule_id for rule in self.rules)
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("Trajectory rule IDs must be unique.")

    def ingest(self, event: SafetyBoxEvent) -> tuple[TrajectoryFinding, ...]:
        """Accept one canonical event and return findings newly emitted for it."""
        previous = self._last_sequence_by_session.get(event.session_id, 0)
        if event.sequence_number <= previous:
            raise TrajectoryOrderingError(
                f"Non-increasing sequence for session {event.session_id}: "
                f"{event.sequence_number} after {previous}."
            )
        self._last_sequence_by_session[event.session_id] = event.sequence_number
        self._processed_event_counts[event.session_id] = (
            self._processed_event_counts.get(event.session_id, 0) + 1
        )
        observation = self._builder.build(event)
        if observation is None:
            return ()
        history = self._history_for(observation)
        history.append(observation)
        emitted: list[TrajectoryFinding] = []
        for rule in self.rules:
            finding = rule.evaluate(tuple(history))
            if finding is None:
                continue
            key = (finding.session_id, finding.rule_id, finding.related_request_ids)
            if key in self._deduplication_keys:
                continue
            self._deduplication_keys.add(key)
            self._findings_by_session.setdefault(finding.session_id, []).append(finding)
            emitted.append(finding)
        return tuple(emitted)

    def evaluate(self, events: tuple[SafetyBoxEvent, ...]) -> tuple[TrajectoryEvaluation, ...]:
        """Ingest an ordered trace and return immutable snapshots by session."""
        for event in events:
            self.ingest(event)
        return tuple(self.snapshot(session_id) for session_id in self._processed_event_counts)

    def snapshot(self, session_id: str) -> TrajectoryEvaluation:
        """Return an immutable finding snapshot for one session."""
        return TrajectoryEvaluation(
            session_id=session_id,
            findings=tuple(self._findings_by_session.get(session_id, ())),
            processed_event_count=self._processed_event_counts.get(session_id, 0),
            rule_ids=tuple(rule.rule_id for rule in self.rules),
        )

    def _history_for(
        self, observation: CompletedActionObservation
    ) -> deque[CompletedActionObservation]:
        key = (observation.session_id, observation.task_id)
        if key not in self._histories:
            self._histories[key] = deque(maxlen=self.window_size)
        return self._histories[key]
