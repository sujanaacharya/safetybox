"""Bounded ordered monitor composing M5 observations with M5.1-B evaluations."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from safetybox.context import ContextEvaluator, ObservationContext, TaskContext
from safetybox.context_trajectory.models import (
    ContextAwareTrajectoryEvaluation,
    ContextAwareTrajectoryFinding,
    ContextualizedObservation,
)
from safetybox.context_trajectory.rules import (
    AccessThenOutboundContextRule,
    ContextAwareTrajectoryRule,
    RepeatedDeniedContextRule,
)
from safetybox.trajectory import CompletedActionObservation


class ContextTrajectoryOrderingError(ValueError):
    """Observations were not supplied in strict per-session canonical order."""


class TaskContextChangedError(ValueError):
    """A session/task stream attempted to change its trusted context."""


@dataclass(slots=True)
class ContextAwareTrajectoryMonitor:
    """Observational deterministic reasoning over bounded session/task-local state."""

    window_size: int = 8
    rules: tuple[ContextAwareTrajectoryRule, ...] = field(
        default_factory=lambda: (
            AccessThenOutboundContextRule(),
            RepeatedDeniedContextRule(),
        )
    )
    context_evaluator: ContextEvaluator = field(default_factory=ContextEvaluator)
    _last_sequence_by_session: dict[str, int] = field(default_factory=dict, init=False)
    _histories: dict[tuple[str, str], deque[ContextualizedObservation]] = field(
        default_factory=dict, init=False
    )
    _contexts: dict[tuple[str, str], TaskContext] = field(default_factory=dict, init=False)
    _findings: dict[tuple[str, str], list[ContextAwareTrajectoryFinding]] = field(
        default_factory=dict, init=False
    )
    _deduplication_keys: set[tuple[str, str, str, tuple[str, ...]]] = field(
        default_factory=set, init=False
    )
    _processed_counts: dict[tuple[str, str], int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        if self.window_size < 1:
            raise ValueError("Context-aware trajectory window_size must be positive.")
        if not self.rules:
            raise ValueError("Context-aware trajectory monitor requires at least one rule.")
        rule_ids = tuple(rule.rule_id for rule in self.rules)
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("Context-aware trajectory rule IDs must be unique.")

    def ingest(
        self,
        observation: CompletedActionObservation,
        task_context: TaskContext,
        observation_context: ObservationContext | None = None,
    ) -> tuple[ContextAwareTrajectoryFinding, ...]:
        """Evaluate and retain one canonical completed observation."""
        previous = self._last_sequence_by_session.get(observation.session_id, 0)
        if observation.sequence_number <= previous:
            raise ContextTrajectoryOrderingError(
                f"Non-increasing sequence for session {observation.session_id}: "
                f"{observation.sequence_number} after {previous}."
            )
        key = (observation.session_id, observation.task_id)
        existing = self._contexts.get(key)
        if existing is not None and existing != task_context:
            raise TaskContextChangedError(
                "Trusted TaskContext changed within one session/task state boundary."
            )
        evaluation = self.context_evaluator.evaluate(
            observation, task_context, observation_context
        )
        self._last_sequence_by_session[observation.session_id] = observation.sequence_number
        self._contexts.setdefault(key, task_context)
        supplied = observation_context or ObservationContext()
        item = ContextualizedObservation(observation, evaluation, supplied)
        history = self._history_for(key)
        history.append(item)
        self._processed_counts[key] = self._processed_counts.get(key, 0) + 1

        emitted: list[ContextAwareTrajectoryFinding] = []
        for rule in self.rules:
            finding = rule.evaluate(tuple(history), task_context)
            if finding is None:
                continue
            deduplication_key = (
                finding.session_id,
                finding.task_id,
                finding.finding_type,
                finding.related_request_ids,
            )
            if deduplication_key in self._deduplication_keys:
                continue
            self._deduplication_keys.add(deduplication_key)
            self._findings.setdefault(key, []).append(finding)
            emitted.append(finding)
        return tuple(emitted)

    def snapshot(
        self, session_id: str, task_id: str
    ) -> ContextAwareTrajectoryEvaluation:
        """Return an immutable snapshot without exposing mutable internal containers."""
        key = (session_id, task_id)
        history = tuple(self._histories.get(key, ()))
        return ContextAwareTrajectoryEvaluation(
            session_id=session_id,
            task_id=task_id,
            findings=tuple(self._findings.get(key, ())),
            recent_observations=tuple(item.observation for item in history),
            context_evaluations=tuple(item.context_evaluation for item in history),
            processed_observation_count=self._processed_counts.get(key, 0),
            rule_ids=tuple(rule.rule_id for rule in self.rules),
        )

    def _history_for(
        self, key: tuple[str, str]
    ) -> deque[ContextualizedObservation]:
        if key not in self._histories:
            self._histories[key] = deque(maxlen=self.window_size)
        return self._histories[key]

