"""Deterministic classification using one context evaluation at a time."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar

from safetybox.context import (
    ContextEvaluation,
    ContextEvaluationStatus,
    ContextEvaluator,
    ContextReason,
    ContextSource,
    ObservationContext,
    TaskContext,
)
from safetybox.models import Decision
from safetybox.trajectory import CompletedActionObservation

BASELINE_IDENTIFIER = "B2-SINGLE-OBSERVATION@1"


class BaselinePrediction(StrEnum):
    """Neutral context-consistency predictions, not safety judgments."""

    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    ABSTAIN = "ABSTAIN"


@dataclass(frozen=True, slots=True)
class SingleObservationBaselineResult:
    """Immutable prediction and audit evidence for one isolated observation."""

    baseline_id: str
    session_id: str
    task_id: str
    request_id: str
    sequence_number: int
    canonical_event_id: str
    context_status: ContextEvaluationStatus
    prediction: BaselinePrediction
    reason_ids: tuple[ContextReason, ...]
    context_sources: tuple[ContextSource, ...]
    observation_action: str
    observation_resource: str
    matched_resource_role_id: str | None
    matched_data_role_ids: tuple[str, ...]
    matched_destination_id: str | None
    matched_destination_purpose_id: str | None
    policy_decision: Decision
    executed: bool


@dataclass(frozen=True, slots=True)
class SingleObservationScenarioResult:
    """Order-free, duplicate-insensitive reduction of isolated predictions."""

    baseline_id: str
    session_id: str
    task_id: str
    prediction: BaselinePrediction
    observation_results: frozenset[SingleObservationBaselineResult]


@dataclass(frozen=True, slots=True)
class SingleObservationBaseline:
    """Stateless executable baseline over frozen single-observation semantics."""

    identifier: ClassVar[str] = BASELINE_IDENTIFIER

    def evaluate(
        self,
        observation: CompletedActionObservation,
        task_context: TaskContext,
        observation_context: ObservationContext | None = None,
    ) -> SingleObservationBaselineResult:
        """Evaluate and classify one observation without retaining it."""
        evaluation = ContextEvaluator().evaluate(observation, task_context, observation_context)
        return self.classify(observation, evaluation)

    def classify(
        self,
        observation: CompletedActionObservation,
        evaluation: ContextEvaluation,
    ) -> SingleObservationBaselineResult:
        """Classify one already evaluated observation after validating its binding."""
        self._validate_binding(observation, evaluation)
        status = evaluation.status
        prediction = self._prediction_for(status)
        reasons = tuple(
            result.reason_id
            for result in evaluation.constraint_results
            if result.status is status
        )
        return SingleObservationBaselineResult(
            baseline_id=self.identifier,
            session_id=observation.session_id,
            task_id=observation.task_id,
            request_id=observation.request_id,
            sequence_number=observation.sequence_number,
            canonical_event_id=observation.canonical_event_id,
            context_status=status,
            prediction=prediction,
            reason_ids=reasons,
            context_sources=evaluation.context_sources,
            observation_action=observation.action,
            observation_resource=observation.resource,
            matched_resource_role_id=evaluation.matched_resource_role_id,
            matched_data_role_ids=evaluation.matched_data_role_ids,
            matched_destination_id=evaluation.matched_destination_id,
            matched_destination_purpose_id=evaluation.matched_destination_purpose_id,
            policy_decision=evaluation.policy_decision,
            executed=evaluation.executed,
        )

    def aggregate(
        self, results: Iterable[SingleObservationBaselineResult]
    ) -> SingleObservationScenarioResult:
        """Reduce isolated results with commutative, idempotent precedence."""
        evidence = frozenset(results)
        if not evidence:
            raise ValueError("Scenario aggregation requires at least one observation result.")
        if any(result.baseline_id != self.identifier for result in evidence):
            raise ValueError("Scenario results must use the same baseline identifier.")
        session_ids = {result.session_id for result in evidence}
        task_ids = {result.task_id for result in evidence}
        if len(session_ids) != 1 or len(task_ids) != 1:
            raise ValueError("Scenario results must share one session_id and task_id.")
        predictions = {result.prediction for result in evidence}
        if BaselinePrediction.POSITIVE in predictions:
            prediction = BaselinePrediction.POSITIVE
        elif BaselinePrediction.ABSTAIN in predictions:
            prediction = BaselinePrediction.ABSTAIN
        else:
            prediction = BaselinePrediction.NEGATIVE
        return SingleObservationScenarioResult(
            baseline_id=self.identifier,
            session_id=next(iter(session_ids)),
            task_id=next(iter(task_ids)),
            prediction=prediction,
            observation_results=evidence,
        )

    @staticmethod
    def _prediction_for(status: ContextEvaluationStatus) -> BaselinePrediction:
        if status is ContextEvaluationStatus.CONTEXT_MISMATCH:
            return BaselinePrediction.POSITIVE
        if status is ContextEvaluationStatus.INSUFFICIENT_CONTEXT:
            return BaselinePrediction.ABSTAIN
        return BaselinePrediction.NEGATIVE

    @staticmethod
    def _validate_binding(
        observation: CompletedActionObservation,
        evaluation: ContextEvaluation,
    ) -> None:
        observation_binding = (
            observation.task_id,
            observation.request_id,
            observation.sequence_number,
            observation.canonical_event_id,
            observation.policy_decision,
            observation.executed,
        )
        evaluation_binding = (
            evaluation.task_id,
            evaluation.request_id,
            evaluation.sequence_number,
            evaluation.canonical_event_id,
            evaluation.policy_decision,
            evaluation.executed,
        )
        if observation_binding != evaluation_binding:
            raise ValueError("ContextEvaluation is not bound to the supplied observation.")
