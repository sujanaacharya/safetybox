"""Small deterministic rules over bounded M5.1-B evaluation history."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from hashlib import sha256
from typing import TypeVar

from safetybox.context import (
    ContextDimension,
    ContextEvaluationStatus,
    ContextSource,
    TaskContext,
)
from safetybox.context_trajectory.models import (
    ContextAwareTrajectoryFinding,
    ContextTrajectoryClassification,
    ContextualizedObservation,
)
from safetybox.models import Decision


class ContextAwareTrajectoryRule(ABC):
    """A stateless rule over one bounded session/task-local history."""

    rule_id: str

    @abstractmethod
    def evaluate(
        self,
        history: Sequence[ContextualizedObservation],
        task_context: TaskContext,
    ) -> ContextAwareTrajectoryFinding | None:
        """Return a finding for a match ending at the newest observation."""


def _finding_id(
    rule_id: str, evidence: Sequence[ContextualizedObservation], finding_type: str
) -> str:
    first = evidence[0].observation
    material = "|".join(
        (
            first.session_id,
            first.task_id,
            rule_id,
            finding_type,
            *(item.observation.request_id for item in evidence),
        )
    )
    return f"{rule_id}:{sha256(material.encode()).hexdigest()[:16]}"


_T = TypeVar("_T")


def _ordered_unique(items: Sequence[_T]) -> tuple[_T, ...]:
    return tuple(dict.fromkeys(items))


def _reasons(evidence: Sequence[ContextualizedObservation]) -> tuple[str, ...]:
    return _ordered_unique(
        tuple(
            result.reason_id.value
            for item in evidence
            for result in item.context_evaluation.constraint_results
            if result.status
            in {
                ContextEvaluationStatus.CONTEXT_MISMATCH,
                ContextEvaluationStatus.INSUFFICIENT_CONTEXT,
            }
        )
    )


def _sources(evidence: Sequence[ContextualizedObservation]) -> tuple[ContextSource, ...]:
    return _ordered_unique(
        tuple(
            source
            for item in evidence
            for source in item.context_evaluation.context_sources
        )
    )


def _resource_roles(evidence: Sequence[ContextualizedObservation]) -> tuple[str, ...]:
    return _ordered_unique(
        tuple(
            role
            for item in evidence
            if (role := item.context_evaluation.matched_resource_role_id) is not None
        )
    )


def _data_roles(evidence: Sequence[ContextualizedObservation]) -> tuple[str, ...]:
    return _ordered_unique(
        tuple(
            role
            for item in evidence
            for role in item.context_evaluation.matched_data_role_ids
        )
    )


def _has_dimension(
    item: ContextualizedObservation, dimension: ContextDimension
) -> bool:
    return any(
        result.dimension is dimension
        and result.status is not ContextEvaluationStatus.NOT_APPLICABLE
        for result in item.context_evaluation.constraint_results
    )


def _lineage_available(item: ContextualizedObservation) -> bool:
    return item.supplied_context.logical_data_flow is not None


class AccessThenOutboundContextRule(ContextAwareTrajectoryRule):
    """CTXTRJ-001: interpreted outbound mismatch after declared-role access."""

    rule_id = "CTXTRJ-001"

    def evaluate(
        self,
        history: Sequence[ContextualizedObservation],
        task_context: TaskContext,
    ) -> ContextAwareTrajectoryFinding | None:
        if len(history) < 2:
            return None
        current = history[-1]
        if not _has_dimension(current, ContextDimension.DESTINATION):
            return None
        accesses = tuple(
            item
            for item in history[:-1]
            if item.observation.executed
            and item.context_evaluation.matched_resource_role_id is not None
        )
        if not accesses:
            return None
        status = current.context_evaluation.status
        if status is ContextEvaluationStatus.CONTEXT_CONSISTENT:
            return None
        if status not in {
            ContextEvaluationStatus.CONTEXT_MISMATCH,
            ContextEvaluationStatus.INSUFFICIENT_CONTEXT,
        }:
            return None
        evidence = (*accesses, current)
        insufficient = status is ContextEvaluationStatus.INSUFFICIENT_CONTEXT
        finding_type = (
            "ACCESS_THEN_OUTBOUND_CONTEXT_INSUFFICIENT"
            if insufficient
            else "ACCESS_THEN_OUTBOUND_CONTEXT_MISMATCH"
        )
        classification = (
            ContextTrajectoryClassification.INSUFFICIENT_CONTEXT
            if insufficient
            else ContextTrajectoryClassification.SUSPICIOUS
        )
        lineage = _lineage_available(current)
        description = (
            "Outbound action occurred after access to declared resource roles, but required "
            "outbound context was insufficient; no payload lineage is inferred."
            if insufficient
            else "Outbound action occurred after access to declared resource roles and its "
            "M5.1-B evaluation found a context mismatch; this ordering does not prove that "
            "accessed data was transferred."
        )
        return _build_finding(
            self.rule_id,
            finding_type,
            classification,
            evidence,
            expected_context=(
                "outbound destination, outcome, data-role, and action-purpose relationships "
                "consistent with trusted task declarations",
            ),
            observed_context=(
                f"task-purpose:{task_context.purpose.purpose_id}",
                f"outbound-status:{status.value}",
                "lineage:logical-declaration" if lineage else "lineage:unavailable",
            ),
            lineage_evidence_available=lineage,
            description=description,
        )


class RepeatedDeniedContextRule(ContextAwareTrajectoryRule):
    """CTXTRJ-002: repeated denied resources interpreted via trusted fallback evidence."""

    rule_id = "CTXTRJ-002"
    threshold = 3

    def evaluate(
        self,
        history: Sequence[ContextualizedObservation],
        task_context: TaskContext,
    ) -> ContextAwareTrajectoryFinding | None:
        if not history:
            return None
        current = history[-1]
        if current.observation.policy_decision is not Decision.DENY:
            return None
        denied = tuple(
            item
            for item in history
            if item.observation.policy_decision is Decision.DENY
            and item.observation.action == current.observation.action
        )
        if len(denied) < self.threshold:
            return None
        matched = denied[-self.threshold :]
        if len({item.observation.resource for item in matched}) < self.threshold:
            return None

        evaluations = tuple(item.context_evaluation for item in matched)
        if any(
            evaluation.status is ContextEvaluationStatus.INSUFFICIENT_CONTEXT
            for evaluation in evaluations
        ):
            return _build_finding(
                self.rule_id,
                "REPEATED_DENIAL_CONTEXT_INSUFFICIENT",
                ContextTrajectoryClassification.INSUFFICIENT_CONTEXT,
                matched,
                expected_context=("trusted bounded fallback declaration covering each attempt",),
                observed_context=("repeated denied distinct-resource attempts",),
                lineage_evidence_available=False,
                description=(
                    "Repeated denied attempts reached the deterministic repetition threshold, "
                    "but required trusted fallback context was insufficient."
                ),
            )

        behavior_ids = tuple(
            evaluation.matched_fallback_behavior_id for evaluation in evaluations
        )
        bound_exceeded = False
        if all(behavior_ids) and len(set(behavior_ids)) == 1:
            behavior_id = behavior_ids[0]
            pattern = next(
                item
                for item in task_context.fallback_patterns
                if item.behavior_id == behavior_id
            )
            matching_attempt_count = sum(
                item.context_evaluation.matched_fallback_behavior_id == behavior_id
                for item in denied
            )
            if (
                pattern.maximum_attempts is None
                or matching_attempt_count <= pattern.maximum_attempts
            ):
                return None
            bound_exceeded = True

        return _build_finding(
            self.rule_id,
            "REPEATED_DENIED_UNDECLARED_PROBING",
            ContextTrajectoryClassification.SUSPICIOUS,
            matched,
            expected_context=("trusted bounded fallback declaration covering each attempt",),
            observed_context=(
                f"action:{current.observation.action}",
                f"distinct-resources:{len({item.observation.resource for item in matched})}",
                "fallback-membership:mismatch-or-bound-exceeded",
            ),
            lineage_evidence_available=False,
            additional_reason_ids=(
                ("CTXTRJ-FALLBACK-BOUND-EXCEEDED",) if bound_exceeded else ()
            ),
            description=(
                "Repeated denied attempts across distinct resources were not covered by one "
                "trusted fallback declaration within its declared bound."
            ),
        )


def _build_finding(
    rule_id: str,
    finding_type: str,
    classification: ContextTrajectoryClassification,
    evidence: Sequence[ContextualizedObservation],
    *,
    expected_context: tuple[str, ...],
    observed_context: tuple[str, ...],
    lineage_evidence_available: bool,
    additional_reason_ids: tuple[str, ...] = (),
    description: str,
) -> ContextAwareTrajectoryFinding:
    observations = tuple(item.observation for item in evidence)
    return ContextAwareTrajectoryFinding(
        finding_id=_finding_id(rule_id, evidence, finding_type),
        session_id=observations[0].session_id,
        task_id=observations[0].task_id,
        rule_id=rule_id,
        finding_type=finding_type,
        classification=classification,
        first_sequence_number=observations[0].sequence_number,
        detection_sequence_number=observations[-1].sequence_number,
        related_request_ids=tuple(item.request_id for item in observations),
        canonical_event_ids=tuple(item.canonical_event_id for item in observations),
        context_reason_ids=_ordered_unique((*_reasons(evidence), *additional_reason_ids)),
        context_sources=_sources(evidence),
        matched_resource_role_ids=_resource_roles(evidence),
        matched_data_role_ids=_data_roles(evidence),
        expected_context=expected_context,
        observed_context=observed_context,
        lineage_evidence_available=lineage_evidence_available,
        description=description,
    )
