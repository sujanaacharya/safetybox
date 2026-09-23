"""Deterministic single-observation interpretation against trusted task context."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar

from safetybox.capabilities import resource_matches
from safetybox.context.models import (
    ContextSource,
    DataFlowConstraint,
    DestinationConstraint,
    FallbackPattern,
    ResourceRole,
    TaskContext,
)
from safetybox.models import Decision
from safetybox.trajectory.models import CompletedActionObservation


class ContextEvaluationError(ValueError):
    """Raised when an observation cannot be evaluated as supplied."""


class TaskContextMismatchError(ContextEvaluationError):
    """Raised when observation and context belong to different tasks."""


class ContextEvaluationStatus(StrEnum):
    """Single-observation interpretation outcomes, not safety classifications."""

    CONTEXT_CONSISTENT = "CONTEXT_CONSISTENT"
    CONTEXT_MISMATCH = "CONTEXT_MISMATCH"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ContextDimension(StrEnum):
    """Independently auditable semantic dimensions."""

    RESOURCE = "resource"
    DESTINATION = "destination"
    OUTCOME = "outcome"
    ACTION_PURPOSE = "action_purpose"
    DATA_ROLE = "data_role"
    DATA_FLOW = "data_flow"
    FALLBACK = "fallback"


class ContextReason(StrEnum):
    """Stable machine-readable reasons for context evaluation evidence."""

    RESOURCE_MATCH = "CTX-RESOURCE-MATCH"
    RESOURCE_UNDECLARED = "CTX-RESOURCE-UNDECLARED"
    RESOURCE_CONTEXT_MISSING = "CTX-RESOURCE-CONTEXT-MISSING"
    DESTINATION_MATCH = "CTX-DESTINATION-MATCH"
    DESTINATION_UNDECLARED = "CTX-DESTINATION-UNDECLARED"
    DESTINATION_ACTION_MISMATCH = "CTX-DESTINATION-ACTION-MISMATCH"
    DESTINATION_CONTEXT_MISSING = "CTX-DESTINATION-CONTEXT-MISSING"
    OUTCOME_MATCH = "CTX-OUTCOME-MATCH"
    OUTCOME_UNDECLARED = "CTX-OUTCOME-UNDECLARED"
    OUTCOME_CONTEXT_MISSING = "CTX-OUTCOME-CONTEXT-MISSING"
    ACTION_PURPOSE_MATCH = "CTX-ACTION-PURPOSE-MATCH"
    ACTION_PURPOSE_MISMATCH = "CTX-ACTION-PURPOSE-MISMATCH"
    ACTION_PURPOSE_CONTEXT_MISSING = "CTX-ACTION-PURPOSE-CONTEXT-MISSING"
    DATA_ROLE_MATCH = "CTX-DATA-ROLE-MATCH"
    DATA_ROLE_MISMATCH = "CTX-DATA-ROLE-MISMATCH"
    DATA_ROLE_CONTEXT_MISSING = "CTX-DATA-ROLE-CONTEXT-MISSING"
    DATA_FLOW_MATCH = "CTX-DATA-FLOW-MATCH"
    DATA_FLOW_MISMATCH = "CTX-DATA-FLOW-MISMATCH"
    DATA_FLOW_CONTEXT_MISSING = "CTX-DATA-FLOW-CONTEXT-MISSING"
    FALLBACK_MATCH = "CTX-FALLBACK-MATCH"
    FALLBACK_UNDECLARED = "CTX-FALLBACK-UNDECLARED"
    FALLBACK_CONTEXT_MISSING = "CTX-FALLBACK-CONTEXT-MISSING"
    NOT_APPLICABLE = "CTX-NOT-APPLICABLE"


@dataclass(frozen=True, slots=True)
class LogicalDataFlow:
    """Supplied logical relationship; this is not runtime byte lineage."""

    source_resource_role_ids: frozenset[str]
    derived_data_role_id: str
    destination_purpose_id: str
    action_purpose_id: str

    def __init__(
        self,
        source_resource_role_ids: Iterable[str],
        derived_data_role_id: str,
        destination_purpose_id: str,
        action_purpose_id: str,
    ) -> None:
        roles = frozenset(source_resource_role_ids)
        if not roles:
            raise ContextEvaluationError("Logical data flow requires a source resource role.")
        for role_id in roles:
            _require_supplied_identifier("Logical data flow source role", role_id)
        _require_supplied_identifier("Logical data flow derived role", derived_data_role_id)
        _require_supplied_identifier(
            "Logical data flow destination purpose", destination_purpose_id
        )
        _require_supplied_identifier("Logical data flow action purpose", action_purpose_id)
        object.__setattr__(self, "source_resource_role_ids", roles)
        object.__setattr__(self, "derived_data_role_id", derived_data_role_id)
        object.__setattr__(self, "destination_purpose_id", destination_purpose_id)
        object.__setattr__(self, "action_purpose_id", action_purpose_id)


@dataclass(frozen=True, slots=True)
class ObservationContext:
    """Optional structured metadata supplied separately from canonical telemetry."""

    action_purpose_id: str | None = None
    data_role_ids: frozenset[str] = frozenset()
    logical_data_flow: LogicalDataFlow | None = None

    def __init__(
        self,
        action_purpose_id: str | None = None,
        data_role_ids: Iterable[str] = (),
        logical_data_flow: LogicalDataFlow | None = None,
    ) -> None:
        if action_purpose_id is not None:
            _require_supplied_identifier("Observation action purpose", action_purpose_id)
        roles = frozenset(data_role_ids)
        for role_id in roles:
            _require_supplied_identifier("Observation data role", role_id)
        object.__setattr__(self, "action_purpose_id", action_purpose_id)
        object.__setattr__(self, "data_role_ids", roles)
        object.__setattr__(self, "logical_data_flow", logical_data_flow)


@dataclass(frozen=True, slots=True)
class ConstraintEvaluation:
    """One deterministic, reason-coded semantic comparison."""

    dimension: ContextDimension
    status: ContextEvaluationStatus
    reason_id: ContextReason
    observed_value: str | None = None
    declaration_id: str | None = None
    source: ContextSource | None = None


@dataclass(frozen=True, slots=True)
class ContextEvaluation:
    """Immutable interpretation of one completed observation."""

    task_id: str
    request_id: str
    sequence_number: int
    canonical_event_id: str
    status: ContextEvaluationStatus
    policy_decision: Decision
    executed: bool
    matched_resource_role_id: str | None
    matched_data_role_ids: tuple[str, ...]
    matched_destination_id: str | None
    matched_destination_purpose_id: str | None
    matched_action_purpose_ids: tuple[str, ...]
    matched_fallback_behavior_id: str | None
    matched_fallback_candidate_scopes: tuple[str, ...]
    context_sources: tuple[ContextSource, ...]
    missing_dimensions: tuple[ContextDimension, ...]
    constraint_results: tuple[ConstraintEvaluation, ...]


@dataclass(frozen=True, slots=True)
class ContextEvaluator:
    """Stateless evaluator for one canonical completed action observation."""

    outbound_actions: ClassVar[frozenset[str]] = frozenset({"network.send"})

    def evaluate(
        self,
        observation: CompletedActionObservation,
        task_context: TaskContext,
        observation_context: ObservationContext | None = None,
    ) -> ContextEvaluation:
        """Relate one observation to declarations without changing authorization."""
        if observation.task_id != task_context.task_id:
            raise TaskContextMismatchError(
                "Observation task_id does not match TaskContext task_id."
            )
        self._validate_terminal_outcome(observation)
        supplied = observation_context or ObservationContext()
        results: list[ConstraintEvaluation] = []
        resource_role: ResourceRole | None = None
        destination: DestinationConstraint | None = None
        fallback: FallbackPattern | None = None

        destination_required = observation.action in self.outbound_actions or any(
            item.action == observation.action for item in task_context.destination_constraints
        )
        if destination_required:
            results.append(self._not_applicable(ContextDimension.RESOURCE))
            destination = self._evaluate_destination(observation, task_context, results)
        else:
            resource_role = self._evaluate_resource(observation, task_context, results)
            results.extend(
                (
                    self._not_applicable(ContextDimension.DESTINATION),
                    self._not_applicable(ContextDimension.OUTCOME),
                    self._not_applicable(ContextDimension.DATA_ROLE),
                    self._not_applicable(ContextDimension.DATA_FLOW),
                )
            )

        self._evaluate_action_purpose(
            observation, task_context, supplied, destination, results
        )
        if destination_required:
            self._evaluate_data_roles_and_flow(supplied, task_context, destination, results)

        if observation.policy_decision is Decision.DENY:
            fallback = self._evaluate_fallback(
                observation, task_context, resource_role, results
            )
        else:
            results.append(self._not_applicable(ContextDimension.FALLBACK))

        status = self._aggregate_status(results)
        missing = tuple(
            result.dimension
            for result in results
            if result.status is ContextEvaluationStatus.INSUFFICIENT_CONTEXT
        )
        data_roles = self._matched_data_roles(resource_role, supplied, destination)
        action_purposes = self._matched_action_purposes(
            observation, supplied, task_context, destination
        )
        sources = self._matched_sources(
            task_context,
            destination,
            data_roles,
            action_purposes,
            (result.source for result in results),
        )
        return ContextEvaluation(
            task_id=observation.task_id,
            request_id=observation.request_id,
            sequence_number=observation.sequence_number,
            canonical_event_id=observation.canonical_event_id,
            status=status,
            policy_decision=observation.policy_decision,
            executed=observation.executed,
            matched_resource_role_id=(resource_role.role_id if resource_role else None),
            matched_data_role_ids=data_roles,
            matched_destination_id=(destination.destination_id if destination else None),
            matched_destination_purpose_id=(
                destination.destination_purpose_id if destination else None
            ),
            matched_action_purpose_ids=action_purposes,
            matched_fallback_behavior_id=(fallback.behavior_id if fallback else None),
            matched_fallback_candidate_scopes=(
                fallback.candidate_resource_scopes if fallback else ()
            ),
            context_sources=sources,
            missing_dimensions=missing,
            constraint_results=tuple(results),
        )

    @staticmethod
    def _validate_terminal_outcome(observation: CompletedActionObservation) -> None:
        valid = (
            observation.policy_decision is Decision.ALLOW and observation.executed
        ) or (
            observation.policy_decision is Decision.DENY and not observation.executed
        )
        if not valid:
            raise ContextEvaluationError(
                "Completed observation has inconsistent policy decision/execution semantics."
            )

    @staticmethod
    def _evaluate_resource(
        observation: CompletedActionObservation,
        context: TaskContext,
        results: list[ConstraintEvaluation],
    ) -> ResourceRole | None:
        if not context.resource_roles:
            results.append(
                ConstraintEvaluation(
                    ContextDimension.RESOURCE,
                    ContextEvaluationStatus.INSUFFICIENT_CONTEXT,
                    ContextReason.RESOURCE_CONTEXT_MISSING,
                    observation.resource,
                )
            )
            return None
        role = context.role_for(observation.resource)
        if role is None:
            results.append(
                ConstraintEvaluation(
                    ContextDimension.RESOURCE,
                    ContextEvaluationStatus.CONTEXT_MISMATCH,
                    ContextReason.RESOURCE_UNDECLARED,
                    observation.resource,
                )
            )
            return None
        results.append(
            ConstraintEvaluation(
                ContextDimension.RESOURCE,
                ContextEvaluationStatus.CONTEXT_CONSISTENT,
                ContextReason.RESOURCE_MATCH,
                observation.resource,
                f"resource-role:{role.resource_scope}:{role.role_id}",
                role.source,
            )
        )
        return role

    @staticmethod
    def _evaluate_destination(
        observation: CompletedActionObservation,
        context: TaskContext,
        results: list[ConstraintEvaluation],
    ) -> DestinationConstraint | None:
        if not context.destination_constraints:
            results.extend(
                (
                    ConstraintEvaluation(
                        ContextDimension.DESTINATION,
                        ContextEvaluationStatus.INSUFFICIENT_CONTEXT,
                        ContextReason.DESTINATION_CONTEXT_MISSING,
                        observation.resource,
                    ),
                    ConstraintEvaluation(
                        ContextDimension.OUTCOME,
                        ContextEvaluationStatus.INSUFFICIENT_CONTEXT,
                        ContextReason.OUTCOME_CONTEXT_MISSING,
                    ),
                )
            )
            return None
        destination = context.destination_policy_for(
            observation.action, observation.resource
        )
        if destination is None:
            reason = (
                ContextReason.DESTINATION_ACTION_MISMATCH
                if any(
                    item.action != observation.action
                    and resource_matches(item.destination_scope, observation.resource)
                    for item in context.destination_constraints
                )
                else ContextReason.DESTINATION_UNDECLARED
            )
            results.extend(
                (
                    ConstraintEvaluation(
                        ContextDimension.DESTINATION,
                        ContextEvaluationStatus.CONTEXT_MISMATCH,
                        reason,
                        observation.resource,
                    ),
                    ContextEvaluator._not_applicable(ContextDimension.OUTCOME),
                )
            )
            return None
        declaration_id = (
            f"destination:{destination.action}:{destination.destination_id}:"
            f"{destination.destination_purpose_id}"
        )
        results.append(
            ConstraintEvaluation(
                ContextDimension.DESTINATION,
                ContextEvaluationStatus.CONTEXT_CONSISTENT,
                ContextReason.DESTINATION_MATCH,
                observation.resource,
                declaration_id,
                destination.source,
            )
        )
        if not context.allowed_outcomes:
            results.append(
                ConstraintEvaluation(
                    ContextDimension.OUTCOME,
                    ContextEvaluationStatus.INSUFFICIENT_CONTEXT,
                    ContextReason.OUTCOME_CONTEXT_MISSING,
                )
            )
        elif not destination.allowed_outcome_ids:
            results.append(
                ConstraintEvaluation(
                    ContextDimension.OUTCOME,
                    ContextEvaluationStatus.CONTEXT_MISMATCH,
                    ContextReason.OUTCOME_UNDECLARED,
                    declaration_id=declaration_id,
                    source=destination.source,
                )
            )
        else:
            results.append(
                ConstraintEvaluation(
                    ContextDimension.OUTCOME,
                    ContextEvaluationStatus.CONTEXT_CONSISTENT,
                    ContextReason.OUTCOME_MATCH,
                    declaration_id=declaration_id,
                    source=destination.source,
                )
            )
        return destination

    @staticmethod
    def _evaluate_action_purpose(
        observation: CompletedActionObservation,
        context: TaskContext,
        supplied: ObservationContext,
        destination: DestinationConstraint | None,
        results: list[ConstraintEvaluation],
    ) -> None:
        declarations = tuple(
            item
            for item in context.expected_action_purposes
            if item.action == observation.action
        )
        permitted = (
            destination.allowed_action_purpose_ids
            if destination is not None
            else frozenset(item.purpose_id for item in declarations)
        )
        if not declarations and supplied.action_purpose_id is None:
            results.append(ContextEvaluator._not_applicable(ContextDimension.ACTION_PURPOSE))
            return
        if not declarations:
            results.append(
                ConstraintEvaluation(
                    ContextDimension.ACTION_PURPOSE,
                    ContextEvaluationStatus.INSUFFICIENT_CONTEXT,
                    ContextReason.ACTION_PURPOSE_CONTEXT_MISSING,
                    supplied.action_purpose_id,
                )
            )
            return
        if supplied.action_purpose_id is not None and supplied.action_purpose_id not in permitted:
            results.append(
                ConstraintEvaluation(
                    ContextDimension.ACTION_PURPOSE,
                    ContextEvaluationStatus.CONTEXT_MISMATCH,
                    ContextReason.ACTION_PURPOSE_MISMATCH,
                    supplied.action_purpose_id,
                )
            )
            return
        matched = (
            supplied.action_purpose_id
            if supplied.action_purpose_id is not None
            else ",".join(sorted(permitted))
        )
        sources = tuple(item.source for item in declarations if item.purpose_id in permitted)
        results.append(
            ConstraintEvaluation(
                ContextDimension.ACTION_PURPOSE,
                ContextEvaluationStatus.CONTEXT_CONSISTENT,
                ContextReason.ACTION_PURPOSE_MATCH,
                matched,
                "action-purpose:" + observation.action + ":" + matched,
                sources[0] if sources else destination.source if destination else None,
            )
        )

    @staticmethod
    def _evaluate_data_roles_and_flow(
        supplied: ObservationContext,
        context: TaskContext,
        destination: DestinationConstraint | None,
        results: list[ConstraintEvaluation],
    ) -> None:
        if not supplied.data_role_ids:
            results.append(ContextEvaluator._not_applicable(ContextDimension.DATA_ROLE))
        elif not context.data_roles or destination is None:
            results.append(
                ConstraintEvaluation(
                    ContextDimension.DATA_ROLE,
                    ContextEvaluationStatus.INSUFFICIENT_CONTEXT,
                    ContextReason.DATA_ROLE_CONTEXT_MISSING,
                    ",".join(sorted(supplied.data_role_ids)),
                )
            )
        elif supplied.data_role_ids <= destination.allowed_data_role_ids:
            results.append(
                ConstraintEvaluation(
                    ContextDimension.DATA_ROLE,
                    ContextEvaluationStatus.CONTEXT_CONSISTENT,
                    ContextReason.DATA_ROLE_MATCH,
                    ",".join(sorted(supplied.data_role_ids)),
                    f"destination:{destination.action}:{destination.destination_id}",
                    destination.source,
                )
            )
        else:
            results.append(
                ConstraintEvaluation(
                    ContextDimension.DATA_ROLE,
                    ContextEvaluationStatus.CONTEXT_MISMATCH,
                    ContextReason.DATA_ROLE_MISMATCH,
                    ",".join(sorted(supplied.data_role_ids)),
                    f"destination:{destination.action}:{destination.destination_id}",
                    destination.source,
                )
            )

        logical_flow = supplied.logical_data_flow
        if logical_flow is None:
            results.append(ContextEvaluator._not_applicable(ContextDimension.DATA_FLOW))
        elif not context.data_flow_constraints:
            results.append(
                ConstraintEvaluation(
                    ContextDimension.DATA_FLOW,
                    ContextEvaluationStatus.INSUFFICIENT_CONTEXT,
                    ContextReason.DATA_FLOW_CONTEXT_MISSING,
                )
            )
        else:
            match = ContextEvaluator._matching_flow(logical_flow, context.data_flow_constraints)
            if match is None:
                results.append(
                    ConstraintEvaluation(
                        ContextDimension.DATA_FLOW,
                        ContextEvaluationStatus.CONTEXT_MISMATCH,
                        ContextReason.DATA_FLOW_MISMATCH,
                    )
                )
            else:
                results.append(
                    ConstraintEvaluation(
                        ContextDimension.DATA_FLOW,
                        ContextEvaluationStatus.CONTEXT_CONSISTENT,
                        ContextReason.DATA_FLOW_MATCH,
                        declaration_id=(
                            "data-flow:"
                            + ",".join(sorted(match.source_resource_role_ids))
                            + f":{match.derived_data_role_id}:{match.destination_purpose_id}"
                        ),
                        source=match.source,
                    )
                )

    @staticmethod
    def _matching_flow(
        supplied: LogicalDataFlow,
        declarations: tuple[DataFlowConstraint, ...],
    ) -> DataFlowConstraint | None:
        for declaration in declarations:
            if (
                supplied.source_resource_role_ids == declaration.source_resource_role_ids
                and supplied.derived_data_role_id == declaration.derived_data_role_id
                and supplied.destination_purpose_id == declaration.destination_purpose_id
                and supplied.action_purpose_id in declaration.allowed_action_purpose_ids
            ):
                return declaration
        return None

    @staticmethod
    def _evaluate_fallback(
        observation: CompletedActionObservation,
        context: TaskContext,
        resource_role: ResourceRole | None,
        results: list[ConstraintEvaluation],
    ) -> FallbackPattern | None:
        if not context.fallback_patterns:
            results.append(
                ConstraintEvaluation(
                    ContextDimension.FALLBACK,
                    ContextEvaluationStatus.INSUFFICIENT_CONTEXT,
                    ContextReason.FALLBACK_CONTEXT_MISSING,
                    observation.resource,
                )
            )
            return None
        fallback = context.fallback_for(observation.action, observation.resource)
        role_compatible = (
            fallback is not None
            and (
                not fallback.candidate_resource_role_ids
                or resource_role is not None
                and resource_role.role_id in fallback.candidate_resource_role_ids
            )
        )
        if fallback is None or not role_compatible:
            results.append(
                ConstraintEvaluation(
                    ContextDimension.FALLBACK,
                    ContextEvaluationStatus.CONTEXT_MISMATCH,
                    ContextReason.FALLBACK_UNDECLARED,
                    observation.resource,
                )
            )
            return None
        results.append(
            ConstraintEvaluation(
                ContextDimension.FALLBACK,
                ContextEvaluationStatus.CONTEXT_CONSISTENT,
                ContextReason.FALLBACK_MATCH,
                observation.resource,
                f"fallback:{fallback.behavior_id}:{fallback.purpose_id}",
                fallback.source,
            )
        )
        return fallback

    @staticmethod
    def _not_applicable(dimension: ContextDimension) -> ConstraintEvaluation:
        return ConstraintEvaluation(
            dimension,
            ContextEvaluationStatus.NOT_APPLICABLE,
            ContextReason.NOT_APPLICABLE,
        )

    @staticmethod
    def _aggregate_status(
        results: list[ConstraintEvaluation],
    ) -> ContextEvaluationStatus:
        statuses = {result.status for result in results}
        if ContextEvaluationStatus.CONTEXT_MISMATCH in statuses:
            return ContextEvaluationStatus.CONTEXT_MISMATCH
        if ContextEvaluationStatus.INSUFFICIENT_CONTEXT in statuses:
            return ContextEvaluationStatus.INSUFFICIENT_CONTEXT
        if ContextEvaluationStatus.CONTEXT_CONSISTENT in statuses:
            return ContextEvaluationStatus.CONTEXT_CONSISTENT
        return ContextEvaluationStatus.NOT_APPLICABLE

    @staticmethod
    def _unique_sources(
        sources: Iterable[ContextSource | None],
    ) -> tuple[ContextSource, ...]:
        result: list[ContextSource] = []
        for source in sources:
            if source is not None and source not in result:
                result.append(source)
        return tuple(result)

    @staticmethod
    def _matched_sources(
        context: TaskContext,
        destination: DestinationConstraint | None,
        data_role_ids: tuple[str, ...],
        action_purpose_ids: tuple[str, ...],
        evidence_sources: Iterable[ContextSource | None],
    ) -> tuple[ContextSource, ...]:
        sources: list[ContextSource | None] = [context.purpose.source, *evidence_sources]
        sources.extend(
            role.source for role in context.data_roles if role.role_id in data_role_ids
        )
        sources.extend(
            declaration.source
            for declaration in context.expected_action_purposes
            if declaration.purpose_id in action_purpose_ids
        )
        if destination is not None:
            sources.extend(
                outcome.source
                for outcome in context.allowed_outcomes
                if outcome.outcome_id in destination.allowed_outcome_ids
            )
        return ContextEvaluator._unique_sources(sources)

    @staticmethod
    def _matched_data_roles(
        resource_role: ResourceRole | None,
        supplied: ObservationContext,
        destination: DestinationConstraint | None,
    ) -> tuple[str, ...]:
        matched = set()
        if resource_role is not None and resource_role.data_role_id is not None:
            matched.add(resource_role.data_role_id)
        if destination is not None:
            matched.update(supplied.data_role_ids & destination.allowed_data_role_ids)
        return tuple(sorted(matched))

    @staticmethod
    def _matched_action_purposes(
        observation: CompletedActionObservation,
        supplied: ObservationContext,
        context: TaskContext,
        destination: DestinationConstraint | None,
    ) -> tuple[str, ...]:
        declared = frozenset(
            item.purpose_id
            for item in context.expected_action_purposes
            if item.action == observation.action
        )
        permitted = (
            declared
            if destination is None
            else declared & destination.allowed_action_purpose_ids
        )
        if supplied.action_purpose_id is not None:
            if supplied.action_purpose_id in permitted:
                return (supplied.action_purpose_id,)
            return ()
        return tuple(sorted(permitted))


def _require_supplied_identifier(label: str, value: str) -> None:
    if not value or value.strip() != value or any(character.isspace() for character in value):
        raise ContextEvaluationError(
            f"{label} must be a non-empty identifier without whitespace."
        )
