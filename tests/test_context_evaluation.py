"""M5.1-B tests for deterministic single-observation context evaluation."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from safetybox import (
    AllowedOutcome,
    Capability,
    CapabilityEvaluator,
    CompletedActionObservation,
    ContextAuthority,
    ContextDimension,
    ContextEvaluation,
    ContextEvaluationStatus,
    ContextEvaluator,
    ContextReason,
    ContextSource,
    DataFlowConstraint,
    DataRole,
    Decision,
    DestinationConstraint,
    EnforcementResult,
    ExpectedActionPurpose,
    FallbackPattern,
    LogicalDataFlow,
    ObservationContext,
    ResourceRole,
    TaskContext,
    TaskContextMismatchError,
    TaskContract,
    TaskPurpose,
)
from safetybox.models import ActionRequest
from safetybox.trajectory import TrajectoryFinding

CONTRACT_SOURCE = ContextSource(ContextAuthority.TASK_CONTRACT, "contract:task-a:v1")
POLICY_SOURCE = ContextSource(ContextAuthority.SYSTEM_POLICY, "policy:destinations:v3")
REGISTRY_SOURCE = ContextSource(
    ContextAuthority.RESOURCE_REGISTRY, "registry:resources:v4"
)


def observation(
    *,
    action: str = "filesystem.read",
    resource: str = "/workspace/project/src/app.py",
    decision: Decision = Decision.ALLOW,
    executed: bool = True,
    task_id: str = "task-a",
    request_id: str = "request-1",
    sequence_number: int = 7,
) -> CompletedActionObservation:
    return CompletedActionObservation(
        session_id="session-1",
        task_id=task_id,
        request_id=request_id,
        actor="agent-1",
        action=action,
        resource=resource,
        policy_decision=decision,
        executed=executed,
        sequence_number=sequence_number,
        canonical_event_id=f"event-{request_id}",
    )


def local_context() -> TaskContext:
    return TaskContext(
        "1",
        "task-a",
        TaskPurpose("local_analysis", CONTRACT_SOURCE),
        data_roles=(DataRole("source_code", REGISTRY_SOURCE),),
        resource_roles=(
            ResourceRole(
                "/workspace/project/**",
                "source_material",
                REGISTRY_SOURCE,
                data_role_id="source_code",
            ),
        ),
        expected_action_purposes=(
            ExpectedActionPurpose("filesystem.read", "code_inspection", CONTRACT_SOURCE),
        ),
    )


def delivery_context(*, destination_scope: str = "api:delivery") -> TaskContext:
    return TaskContext(
        "1",
        "task-a",
        TaskPurpose("report_delivery", CONTRACT_SOURCE),
        allowed_outcomes=(AllowedOutcome("delivered_report", CONTRACT_SOURCE),),
        data_roles=(DataRole("generated_report", REGISTRY_SOURCE),),
        destination_constraints=(
            DestinationConstraint(
                "network.send",
                destination_scope,
                "delivery-api",
                "generated_report_delivery",
                POLICY_SOURCE,
                allowed_data_role_ids=("generated_report",),
                allowed_outcome_ids=("delivered_report",),
                allowed_action_purpose_ids=("report_delivery",),
            ),
        ),
        expected_action_purposes=(
            ExpectedActionPurpose("network.send", "report_delivery", CONTRACT_SOURCE),
        ),
    )


def fallback_context() -> TaskContext:
    return TaskContext(
        "1",
        "task-a",
        TaskPurpose("compatibility_check", CONTRACT_SOURCE),
        resource_roles=(
            ResourceRole("/opt/compat/**", "compat_candidate", REGISTRY_SOURCE),
            ResourceRole("/etc/**", "system_configuration", REGISTRY_SOURCE),
        ),
        expected_action_purposes=(
            ExpectedActionPurpose(
                "filesystem.read", "compatibility_lookup", CONTRACT_SOURCE
            ),
        ),
        fallback_patterns=(
            FallbackPattern(
                "filesystem.read",
                ("/opt/compat/**",),
                ("compat_candidate",),
                "compatibility_lookup",
                "declared_fallback_lookup",
                CONTRACT_SOURCE,
                maximum_attempts=3,
            ),
        ),
    )


def result_for_dimension(
    evaluation: ContextEvaluation, dimension: ContextDimension
):
    return next(
        result for result in evaluation.constraint_results if result.dimension is dimension
    )


def test_resource_and_data_roles_resolve_with_provenance() -> None:
    result = ContextEvaluator().evaluate(observation(), local_context())

    assert result.status is ContextEvaluationStatus.CONTEXT_CONSISTENT
    assert result.matched_resource_role_id == "source_material"
    assert result.matched_data_role_ids == ("source_code",)
    assert REGISTRY_SOURCE in result.context_sources
    assert result_for_dimension(result, ContextDimension.RESOURCE).source == REGISTRY_SOURCE
    data_role = result_for_dimension(result, ContextDimension.DATA_ROLE)
    assert data_role.reason_id is ContextReason.DATA_ROLE_MATCH
    assert data_role.declaration_id == "data-role:source_code"
    assert data_role.source == REGISTRY_SOURCE


def test_database_resource_and_data_roles_use_the_same_generic_lookup() -> None:
    context = TaskContext(
        "1",
        "task-a",
        TaskPurpose("metrics_review", CONTRACT_SOURCE),
        data_roles=(DataRole("analytics_data", REGISTRY_SOURCE),),
        resource_roles=(
            ResourceRole(
                "database:metrics",
                "analysis_input",
                REGISTRY_SOURCE,
                data_role_id="analytics_data",
            ),
        ),
    )

    result = ContextEvaluator().evaluate(
        observation(action="database.query", resource="database:metrics"), context
    )

    assert result.status is ContextEvaluationStatus.CONTEXT_CONSISTENT
    assert result.matched_resource_role_id == "analysis_input"
    assert result.matched_data_role_ids == ("analytics_data",)


def test_resource_scope_boundary_is_preserved() -> None:
    result = ContextEvaluator().evaluate(
        observation(resource="/workspace/project-secret/src/app.py"), local_context()
    )

    assert result.status is ContextEvaluationStatus.CONTEXT_MISMATCH
    assert result_for_dimension(result, ContextDimension.RESOURCE).reason_id is (
        ContextReason.RESOURCE_UNDECLARED
    )


def test_declared_destination_and_supplied_data_role_are_consistent() -> None:
    result = ContextEvaluator().evaluate(
        observation(action="network.send", resource="api:delivery"),
        delivery_context(),
        ObservationContext(data_role_ids=("generated_report",)),
    )

    assert result.status is ContextEvaluationStatus.CONTEXT_CONSISTENT
    assert result.matched_destination_id == "delivery-api"
    assert result.matched_destination_purpose_id == "generated_report_delivery"
    assert result.matched_data_role_ids == ("generated_report",)
    assert POLICY_SOURCE in result.context_sources


def test_undeclared_destination_is_a_mismatch_when_rules_exist() -> None:
    result = ContextEvaluator().evaluate(
        observation(action="network.send", resource="api:other"), delivery_context()
    )

    assert result.status is ContextEvaluationStatus.CONTEXT_MISMATCH
    assert result_for_dimension(result, ContextDimension.DESTINATION).reason_id is (
        ContextReason.DESTINATION_UNDECLARED
    )
    assert POLICY_SOURCE in result.context_sources


def test_destination_without_action_purpose_relationship_is_a_mismatch() -> None:
    context = TaskContext(
        "1",
        "task-a",
        TaskPurpose("report_delivery", CONTRACT_SOURCE),
        allowed_outcomes=(AllowedOutcome("delivered_report", CONTRACT_SOURCE),),
        destination_constraints=(
            DestinationConstraint(
                "network.send",
                "api:delivery",
                "delivery-api",
                "generated_report_delivery",
                POLICY_SOURCE,
                allowed_outcome_ids=("delivered_report",),
            ),
        ),
        expected_action_purposes=(
            ExpectedActionPurpose("network.send", "report_delivery", CONTRACT_SOURCE),
        ),
    )

    result = ContextEvaluator().evaluate(
        observation(action="network.send", resource="api:delivery"), context
    )

    assert result.status is ContextEvaluationStatus.CONTEXT_MISMATCH
    assert result_for_dimension(
        result, ContextDimension.ACTION_PURPOSE
    ).reason_id is ContextReason.ACTION_PURPOSE_MISMATCH


def test_action_purpose_mismatch_is_reason_coded() -> None:
    result = ContextEvaluator().evaluate(
        observation(action="network.send", resource="api:delivery"),
        delivery_context(),
        ObservationContext(action_purpose_id="dependency_metadata_lookup"),
    )

    assert result.status is ContextEvaluationStatus.CONTEXT_MISMATCH
    purpose = result_for_dimension(result, ContextDimension.ACTION_PURPOSE)
    assert purpose.reason_id is ContextReason.ACTION_PURPOSE_MISMATCH
    assert purpose.observed_value == "dependency_metadata_lookup"


def test_missing_destination_context_is_insufficient_not_mismatch() -> None:
    context = TaskContext(
        "1", "task-a", TaskPurpose("local_analysis", CONTRACT_SOURCE)
    )

    result = ContextEvaluator().evaluate(
        observation(action="network.send", resource="api:delivery"), context
    )

    assert result.status is ContextEvaluationStatus.INSUFFICIENT_CONTEXT
    assert ContextDimension.DESTINATION in result.missing_dimensions
    assert result_for_dimension(result, ContextDimension.DESTINATION).reason_id is (
        ContextReason.DESTINATION_CONTEXT_MISSING
    )


def test_destination_is_not_applicable_to_local_action() -> None:
    result = ContextEvaluator().evaluate(observation(), local_context())

    destination = result_for_dimension(result, ContextDimension.DESTINATION)
    assert destination.status is ContextEvaluationStatus.NOT_APPLICABLE
    assert ContextDimension.DESTINATION not in result.missing_dimensions


def test_declared_fallback_matches_one_denied_observation() -> None:
    result = ContextEvaluator().evaluate(
        observation(
            resource="/opt/compat/v2/config",
            decision=Decision.DENY,
            executed=False,
        ),
        fallback_context(),
    )

    assert result.status is ContextEvaluationStatus.CONTEXT_CONSISTENT
    assert result.matched_fallback_behavior_id == "declared_fallback_lookup"
    assert result.matched_fallback_candidate_scopes == ("/opt/compat/**",)
    assert result_for_dimension(result, ContextDimension.FALLBACK).reason_id is (
        ContextReason.FALLBACK_MATCH
    )


def test_unrelated_denied_observation_does_not_match_fallback() -> None:
    result = ContextEvaluator().evaluate(
        observation(resource="/etc/shadow", decision=Decision.DENY, executed=False),
        fallback_context(),
    )

    assert result.status is ContextEvaluationStatus.CONTEXT_MISMATCH
    assert result.matched_fallback_behavior_id is None
    assert result_for_dimension(result, ContextDimension.FALLBACK).reason_id is (
        ContextReason.FALLBACK_UNDECLARED
    )


def test_supplied_purpose_must_match_the_fallback_declaration() -> None:
    context = TaskContext(
        "1",
        "task-a",
        TaskPurpose("compatibility_check", CONTRACT_SOURCE),
        resource_roles=(
            ResourceRole("/opt/compat/**", "compat_candidate", REGISTRY_SOURCE),
        ),
        expected_action_purposes=(
            ExpectedActionPurpose(
                "filesystem.read", "compatibility_lookup", CONTRACT_SOURCE
            ),
            ExpectedActionPurpose("filesystem.read", "diagnostic_lookup", CONTRACT_SOURCE),
        ),
        fallback_patterns=(
            FallbackPattern(
                "filesystem.read",
                ("/opt/compat/**",),
                ("compat_candidate",),
                "compatibility_lookup",
                "declared_fallback_lookup",
                CONTRACT_SOURCE,
                maximum_attempts=3,
            ),
        ),
    )

    result = ContextEvaluator().evaluate(
        observation(
            resource="/opt/compat/v2/config",
            decision=Decision.DENY,
            executed=False,
        ),
        context,
        ObservationContext(action_purpose_id="diagnostic_lookup"),
    )

    assert result.status is ContextEvaluationStatus.CONTEXT_MISMATCH
    assert result.matched_fallback_behavior_id is None
    assert result_for_dimension(result, ContextDimension.FALLBACK).reason_id is (
        ContextReason.FALLBACK_PURPOSE_MISMATCH
    )


def test_task_id_mismatch_is_rejected() -> None:
    with pytest.raises(TaskContextMismatchError, match="task_id"):
        ContextEvaluator().evaluate(observation(task_id="task-b"), local_context())


def test_equivalent_inputs_produce_equivalent_immutable_results() -> None:
    evaluator = ContextEvaluator()
    first = evaluator.evaluate(observation(), local_context())
    second = evaluator.evaluate(observation(), local_context())

    assert first == second
    with pytest.raises(FrozenInstanceError):
        first.status = ContextEvaluationStatus.CONTEXT_MISMATCH  # type: ignore[misc]


def test_evaluator_is_stateless_across_observations() -> None:
    evaluator = ContextEvaluator()
    first = evaluator.evaluate(observation(request_id="first"), local_context())
    evaluator.evaluate(
        observation(
            request_id="denied",
            resource="/etc/shadow",
            decision=Decision.DENY,
            executed=False,
        ),
        fallback_context(),
    )
    repeated = evaluator.evaluate(observation(request_id="first"), local_context())

    assert first == repeated
    assert not hasattr(evaluator, "__dict__")


def test_context_evaluation_cannot_change_authorization_outcome() -> None:
    request = ActionRequest(
        "request-1",
        "session-1",
        "task-a",
        "agent-1",
        "network.send",
        "api:delivery",
    )
    capability = Capability("filesystem.read", "/workspace/project/**")
    contract = TaskContract("task-a", "no outbound authority", (capability,))
    policy_decision = CapabilityEvaluator().evaluate(contract, request)
    enforcement_result = EnforcementResult(request, policy_decision, executed=False)
    authority_snapshot = (contract, capability, policy_decision, enforcement_result)
    denied = observation(
        action=request.action,
        resource=request.resource,
        decision=policy_decision.decision,
        executed=False,
    )

    result = ContextEvaluator().evaluate(denied, delivery_context())

    assert result_for_dimension(result, ContextDimension.DESTINATION).status is (
        ContextEvaluationStatus.CONTEXT_CONSISTENT
    )
    assert result.policy_decision is Decision.DENY
    assert result.executed is False
    assert policy_decision.decision is Decision.DENY
    assert (contract, capability, policy_decision, enforcement_result) == authority_snapshot


def test_same_observation_evaluates_differently_under_different_contexts() -> None:
    same_observation = observation(action="network.send", resource="api:delivery")
    local = TaskContext(
        "1",
        "task-a",
        TaskPurpose("local_analysis", CONTRACT_SOURCE),
        allowed_outcomes=(AllowedOutcome("local_findings", CONTRACT_SOURCE),),
        destination_constraints=(
            DestinationConstraint(
                "network.send",
                "api:dependency-index",
                "dependency-index",
                "dependency_metadata",
                POLICY_SOURCE,
                allowed_outcome_ids=("local_findings",),
            ),
        ),
    )

    local_result = ContextEvaluator().evaluate(same_observation, local)
    delivery_result = ContextEvaluator().evaluate(same_observation, delivery_context())

    assert local_result.status is ContextEvaluationStatus.CONTEXT_MISMATCH
    assert delivery_result.status is ContextEvaluationStatus.CONTEXT_CONSISTENT
    assert local_result.request_id == delivery_result.request_id
    assert local_result.sequence_number == delivery_result.sequence_number


def test_missing_destination_and_violating_destination_are_distinct() -> None:
    outbound = observation(action="network.send", resource="api:delivery")
    absent = TaskContext(
        "1", "task-a", TaskPurpose("local_analysis", CONTRACT_SOURCE)
    )
    declared_elsewhere = delivery_context(destination_scope="api:other")

    missing = ContextEvaluator().evaluate(outbound, absent)
    mismatch = ContextEvaluator().evaluate(outbound, declared_elsewhere)

    assert missing.status is ContextEvaluationStatus.INSUFFICIENT_CONTEXT
    assert mismatch.status is ContextEvaluationStatus.CONTEXT_MISMATCH


def test_evaluation_is_not_a_trajectory_finding() -> None:
    result = ContextEvaluator().evaluate(observation(), local_context())

    assert isinstance(result, ContextEvaluation)
    assert not isinstance(result, TrajectoryFinding)
    assert not hasattr(result, "classification")
    assert not hasattr(result, "finding_id")


def test_supplied_logical_flow_is_compared_but_not_inferred() -> None:
    context = TaskContext(
        "1",
        "task-a",
        TaskPurpose("report_delivery", CONTRACT_SOURCE),
        allowed_outcomes=(AllowedOutcome("delivered_report", CONTRACT_SOURCE),),
        data_roles=(
            DataRole("source_code", REGISTRY_SOURCE),
            DataRole("generated_report", REGISTRY_SOURCE),
        ),
        resource_roles=(
            ResourceRole(
                "/workspace/project/**",
                "source_material",
                REGISTRY_SOURCE,
                "source_code",
            ),
        ),
        destination_constraints=(
            DestinationConstraint(
                "network.send",
                "api:delivery",
                "delivery-api",
                "generated_report_delivery",
                POLICY_SOURCE,
                allowed_data_role_ids=("generated_report",),
                allowed_outcome_ids=("delivered_report",),
                allowed_action_purpose_ids=("report_delivery",),
            ),
        ),
        data_flow_constraints=(
            DataFlowConstraint(
                ("source_material",),
                "generated_report",
                "generated_report_delivery",
                ("report_delivery",),
                CONTRACT_SOURCE,
            ),
        ),
        expected_action_purposes=(
            ExpectedActionPurpose("network.send", "report_delivery", CONTRACT_SOURCE),
        ),
    )
    outbound = observation(action="network.send", resource="api:delivery")
    declared = LogicalDataFlow(
        ("source_material",),
        "generated_report",
        "generated_report_delivery",
        "report_delivery",
    )
    conflicting = LogicalDataFlow(
        ("source_material",),
        "generated_report",
        "other_destination_purpose",
        "report_delivery",
    )

    matched = ContextEvaluator().evaluate(
        outbound, context, ObservationContext(logical_data_flow=declared)
    )
    mismatched = ContextEvaluator().evaluate(
        outbound, context, ObservationContext(logical_data_flow=conflicting)
    )

    assert result_for_dimension(matched, ContextDimension.DATA_FLOW).reason_id is (
        ContextReason.DATA_FLOW_MATCH
    )
    assert result_for_dimension(mismatched, ContextDimension.DATA_FLOW).reason_id is (
        ContextReason.DATA_FLOW_MISMATCH
    )
    assert matched.status is ContextEvaluationStatus.CONTEXT_CONSISTENT
    assert mismatched.status is ContextEvaluationStatus.CONTEXT_MISMATCH
