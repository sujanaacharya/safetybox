"""Fixed bounded B4 monitor, separate from frozen M5.1-C."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from safetybox.b4.models import (
    B4_CONFIG,
    B4ContextualizedObservation,
    B4Evaluation,
    B4HistoricalConstraints,
    B4StateSnapshot,
    B4TrajectoryFinding,
    B4VersionInfo,
    SemanticEventBinding,
)
from safetybox.b4.rules import analyze_window
from safetybox.b4.validation import task_context_reference
from safetybox.context import (
    ContextEvaluation,
    ContextEvaluator,
    ObservationContext,
    TaskContext,
)
from safetybox.trajectory import CompletedActionObservation


class B4Error(ValueError):
    """Base class for explicit B4 infrastructure and binding failures."""


class B4OrderingError(B4Error):
    """Canonical sequence numbers were not strictly increasing per session."""


class B4TaskBindingError(B4Error):
    """Observation, TaskContext, and history context task IDs do not agree."""


class B4ContextChangedError(B4Error):
    """An active key attempted to replace either immutable context value."""


class B4CapacityError(B4Error):
    """The fixed active-key capacity was exhausted."""


@dataclass(slots=True)
class _KeyState:
    task_context: TaskContext
    history_context: B4HistoricalConstraints
    history: deque[B4ContextualizedObservation] = field(default_factory=deque)
    findings: deque[B4TrajectoryFinding] = field(default_factory=deque)
    prefix_evicted: bool = False
    finding_retention_truncated: bool = False


@dataclass(slots=True)
class B4Monitor:
    """Observational deterministic monitor with the frozen B4-CONFIG@1 bounds."""

    context_evaluator: ContextEvaluator = field(default_factory=ContextEvaluator)
    _last_sequence_by_session: dict[str, int] = field(default_factory=dict, init=False)
    _states: dict[tuple[str, str], _KeyState] = field(default_factory=dict, init=False)

    @property
    def version_info(self) -> B4VersionInfo:
        return B4VersionInfo()

    def observe(
        self,
        observation: CompletedActionObservation,
        task_context: TaskContext,
        history_context: B4HistoricalConstraints,
        observation_context: ObservationContext | None = None,
    ) -> B4Evaluation:
        """Interpret and retain one completed observation without affecting authority."""
        self._validate_task_binding(observation, task_context, history_context)
        previous = self._last_sequence_by_session.get(observation.session_id)
        if previous is not None and observation.sequence_number <= previous:
            raise B4OrderingError(
                f"Non-increasing sequence for session {observation.session_id}: "
                f"{observation.sequence_number} after {previous}."
            )
        key = (observation.session_id, observation.task_id)
        state = self._states.get(key)
        if state is None:
            if len(self._states) >= B4_CONFIG.max_active_keys:
                raise B4CapacityError(
                    f"B4 active-key capacity {B4_CONFIG.max_active_keys} is exhausted."
                )
        elif (
            state.task_context != task_context
            or state.history_context != history_context
        ):
            raise B4ContextChangedError(
                "TaskContext or B4 history context changed for an active session/task key."
            )

        evaluation = self.context_evaluator.evaluate(
            observation, task_context, observation_context
        )
        reference_matches = (
            history_context.task_context_reference == task_context_reference(task_context)
        )
        if reference_matches:
            binding, ambiguous = self._semantic_binding(
                observation, evaluation, task_context, history_context
            )
            event_id = binding.semantic_event_id if binding is not None else None
            binding_id = (
                "B4-AMBIGUOUS-SEMANTIC-EVENT"
                if ambiguous
                else binding.binding_id if binding is not None else None
            )
        else:
            event_id = None
            binding_id = "B4-CONTEXT-REFERENCE-MISMATCH"
        item = B4ContextualizedObservation(
            observation, evaluation, event_id, binding_id
        )
        if state is None:
            state = _KeyState(task_context, history_context)
            self._states[key] = state
        if len(state.history) == B4_CONFIG.window_size:
            state.history.popleft()
            state.prefix_evicted = True
        state.history.append(item)
        self._last_sequence_by_session[observation.session_id] = observation.sequence_number

        analysis = analyze_window(
            tuple(state.history),
            task_context,
            history_context,
            prefix_evicted=state.prefix_evicted,
        )
        emitted: list[B4TrajectoryFinding] = []
        retained_ids = {finding.finding_id for finding in state.findings}
        for finding in analysis.findings:
            if finding.finding_id in retained_ids:
                continue
            if len(state.findings) == B4_CONFIG.max_findings:
                state.findings.popleft()
                state.finding_retention_truncated = True
            state.findings.append(finding)
            retained_ids.add(finding.finding_id)
            emitted.append(finding)
        return self._evaluation(key, analysis.state, tuple(emitted))

    def snapshot(self, session_id: str, task_id: str) -> B4Evaluation:
        """Return an immutable snapshot copied from current bounded raw state."""
        key = (session_id, task_id)
        state = self._states.get(key)
        if state is None:
            return B4Evaluation(
                session_id,
                task_id,
                (),
                (),
                B4StateSnapshot(None, (), (), (), (), (), (), (), (), False),
                None,
                None,
                None,
                (),
                (),
                False,
            )
        analysis = analyze_window(
            tuple(state.history),
            state.task_context,
            state.history_context,
            prefix_evicted=state.prefix_evicted,
        )
        return self._evaluation(key, analysis.state, ())

    def close(self, session_id: str, task_id: str) -> None:
        """Explicitly discard one key, including all bounded semantic state."""
        self._states.pop((session_id, task_id), None)
        if not any(key_session == session_id for key_session, _ in self._states):
            self._last_sequence_by_session.pop(session_id, None)

    def _evaluation(
        self,
        key: tuple[str, str],
        snapshot: B4StateSnapshot,
        emitted: tuple[B4TrajectoryFinding, ...],
    ) -> B4Evaluation:
        state = self._states[key]
        latest = state.history[-1] if state.history else None
        return B4Evaluation(
            session_id=key[0],
            task_id=key[1],
            emitted_findings=emitted,
            retained_findings=tuple(state.findings),
            state=snapshot,
            context_evaluation=latest.context_evaluation if latest is not None else None,
            semantic_event_id=latest.semantic_event_id if latest is not None else None,
            active_phase_id=snapshot.active_phase_id,
            accumulated_role_group_ids=snapshot.accumulated_role_group_ids,
            fallback_episodes=snapshot.fallback_episodes,
            finding_retention_truncated=state.finding_retention_truncated,
        )

    @staticmethod
    def _validate_task_binding(
        observation: CompletedActionObservation,
        task_context: TaskContext,
        history_context: B4HistoricalConstraints,
    ) -> None:
        if observation.task_id != task_context.task_id:
            raise B4TaskBindingError("Observation task_id does not match TaskContext task_id.")
        if history_context.task_id != task_context.task_id:
            raise B4TaskBindingError("B4 history context task_id does not match TaskContext.")

    @staticmethod
    def _semantic_binding(
        observation: CompletedActionObservation,
        evaluation: ContextEvaluation,
        task_context: TaskContext,
        history_context: B4HistoricalConstraints,
    ) -> tuple[SemanticEventBinding | None, bool]:
        outcome_ids: frozenset[str] = frozenset()
        if evaluation.matched_destination_id is not None:
            matching_destinations = tuple(
                destination
                for destination in task_context.destination_constraints
                if destination.action == observation.action
                and destination.destination_id == evaluation.matched_destination_id
            )
            if len(matching_destinations) == 1:
                outcome_ids = matching_destinations[0].allowed_outcome_ids
        matches = tuple(
            binding
            for binding in history_context.semantic_event_bindings
            if binding.action == observation.action
            and (
                binding.resource_role_id is None
                or binding.resource_role_id == evaluation.matched_resource_role_id
            )
            and (
                binding.data_role_id is None
                or binding.data_role_id in evaluation.matched_data_role_ids
            )
            and (
                binding.destination_id is None
                or binding.destination_id == evaluation.matched_destination_id
            )
            and (
                binding.action_purpose_id is None
                or binding.action_purpose_id in evaluation.matched_action_purpose_ids
            )
            and (binding.outcome_id is None or binding.outcome_id in outcome_ids)
        )
        if len(matches) > 1:
            return None, True
        return (matches[0] if matches else None), False
