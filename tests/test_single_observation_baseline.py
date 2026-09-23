"""Tests for the frozen history-free single-observation baseline."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, replace

import pytest

import safetybox.baselines.single_observation as baseline_module
from safetybox import (
    BASELINE_IDENTIFIER,
    AllowedOutcome,
    BaselinePrediction,
    Capability,
    CapabilityEvaluator,
    CompletedActionObservation,
    ContextAuthority,
    ContextDimension,
    ContextEvaluationStatus,
    ContextEvaluator,
    ContextReason,
    ContextSource,
    Decision,
    DestinationConstraint,
    EnforcementResult,
    ResourceRole,
    SingleObservationBaseline,
    SingleObservationBaselineResult,
    SingleObservationScenarioResult,
    TaskContext,
    TaskContextMismatchError,
    TaskContract,
    TaskPurpose,
)
from safetybox.context import ConstraintEvaluation
from safetybox.models import ActionRequest
from safetybox.trajectory import TrajectoryFinding

CONTRACT_SOURCE = ContextSource(ContextAuthority.TASK_CONTRACT, "contract:task:v1")
REGISTRY_SOURCE = ContextSource(ContextAuthority.RESOURCE_REGISTRY, "registry:roles:v1")
POLICY_SOURCE = ContextSource(ContextAuthority.SYSTEM_POLICY, "policy:destinations:v1")


def observation(
    *,
    request_id: str = "request-a",
    action: str = "filesystem.read",
    resource: str = "/workspace/a",
    task_id: str = "task-a",
    sequence_number: int = 1,
    decision: Decision = Decision.ALLOW,
    executed: bool = True,
) -> CompletedActionObservation:
    return CompletedActionObservation(
        session_id="session-a",
        task_id=task_id,
        request_id=request_id,
        actor="agent-a",
        action=action,
        resource=resource,
        policy_decision=decision,
        executed=executed,
        sequence_number=sequence_number,
        canonical_event_id=f"event-{request_id}",
    )


def local_context(*, source_reference: str = "registry:roles:v1") -> TaskContext:
    source = ContextSource(ContextAuthority.RESOURCE_REGISTRY, source_reference)
    return TaskContext(
        "1",
        "task-a",
        TaskPurpose("document_review", CONTRACT_SOURCE),
        resource_roles=(ResourceRole("/workspace/**", "workspace_input", source),),
    )


def outbound_context() -> TaskContext:
    return TaskContext(
        "1",
        "task-a",
        TaskPurpose("report_delivery", CONTRACT_SOURCE),
        allowed_outcomes=(AllowedOutcome("report_delivered", CONTRACT_SOURCE),),
        destination_constraints=(
            DestinationConstraint(
                "network.send",
                "api:delivery",
                "delivery-service",
                "report_delivery",
                POLICY_SOURCE,
                allowed_outcome_ids=("report_delivered",),
            ),
        ),
    )


def test_baseline_construction_and_version_are_frozen() -> None:
    baseline = SingleObservationBaseline()

    assert baseline.identifier == "B2-SINGLE-OBSERVATION@1"
    assert BASELINE_IDENTIFIER == baseline.identifier
    assert not inspect.signature(SingleObservationBaseline).parameters
    assert not hasattr(baseline, "__dict__")


def test_one_context_mismatch_is_positive_with_reason_evidence() -> None:
    result = SingleObservationBaseline().evaluate(
        observation(resource="/outside/a"), local_context()
    )

    assert result.context_status is ContextEvaluationStatus.CONTEXT_MISMATCH
    assert result.prediction is BaselinePrediction.POSITIVE
    assert result.reason_ids == (ContextReason.RESOURCE_UNDECLARED,)
    assert CONTRACT_SOURCE in result.context_sources
    assert REGISTRY_SOURCE in result.context_sources


def test_one_context_consistent_observation_is_negative() -> None:
    result = SingleObservationBaseline().evaluate(observation(), local_context())

    assert result.context_status is ContextEvaluationStatus.CONTEXT_CONSISTENT
    assert result.prediction is BaselinePrediction.NEGATIVE
    assert ContextReason.RESOURCE_MATCH in result.reason_ids


def test_insufficient_context_abstains() -> None:
    incomplete = TaskContext(
        "1", "task-a", TaskPurpose("report_delivery", CONTRACT_SOURCE)
    )
    result = SingleObservationBaseline().evaluate(
        observation(action="network.send", resource="api:delivery"), incomplete
    )

    assert result.context_status is ContextEvaluationStatus.INSUFFICIENT_CONTEXT
    assert result.prediction is BaselinePrediction.ABSTAIN
    assert ContextReason.DESTINATION_CONTEXT_MISSING in result.reason_ids


def test_not_applicable_is_explicit_negative_not_mismatch() -> None:
    baseline = SingleObservationBaseline()
    item = observation()
    evaluation = ContextEvaluator().evaluate(item, local_context())
    not_applicable = replace(
        evaluation,
        status=ContextEvaluationStatus.NOT_APPLICABLE,
        constraint_results=(
            ConstraintEvaluation(
                ContextDimension.DATA_FLOW,
                ContextEvaluationStatus.NOT_APPLICABLE,
                ContextReason.NOT_APPLICABLE,
            ),
        ),
    )

    result = baseline.classify(item, not_applicable)

    assert result.context_status is ContextEvaluationStatus.NOT_APPLICABLE
    assert result.prediction is BaselinePrediction.NEGATIVE
    assert result.reason_ids == (ContextReason.NOT_APPLICABLE,)


def test_matched_roles_destination_and_provenance_are_preserved() -> None:
    baseline = SingleObservationBaseline()
    local = baseline.evaluate(observation(), local_context())
    outbound = baseline.evaluate(
        observation(action="network.send", resource="api:delivery"), outbound_context()
    )

    assert local.matched_resource_role_id == "workspace_input"
    assert local.observation_action == "filesystem.read"
    assert local.observation_resource == "/workspace/a"
    assert outbound.matched_destination_id == "delivery-service"
    assert outbound.matched_destination_purpose_id == "report_delivery"
    assert POLICY_SOURCE in outbound.context_sources


def test_task_context_binding_is_enforced() -> None:
    with pytest.raises(TaskContextMismatchError, match="task_id"):
        SingleObservationBaseline().evaluate(
            observation(task_id="task-b"), local_context()
        )


def test_equivalent_inputs_are_deterministic_and_results_are_immutable() -> None:
    baseline = SingleObservationBaseline()

    first = baseline.evaluate(observation(), local_context())
    second = baseline.evaluate(observation(), local_context())

    assert first == second
    with pytest.raises(FrozenInstanceError):
        first.prediction = BaselinePrediction.POSITIVE  # type: ignore[misc]


def test_context_classification_does_not_modify_authorization() -> None:
    request = ActionRequest(
        "request-a", "session-a", "task-a", "agent-a", "network.send", "api:delivery"
    )
    capability = Capability("filesystem.read", "/workspace/**")
    contract = TaskContract("task-a", "local work", (capability,))
    policy = CapabilityEvaluator().evaluate(contract, request)
    enforcement = EnforcementResult(request, policy, executed=False)
    before = (contract, capability, policy, enforcement)
    denied = observation(
        action=request.action,
        resource=request.resource,
        decision=policy.decision,
        executed=False,
    )

    result = SingleObservationBaseline().evaluate(denied, outbound_context())

    assert result.policy_decision is Decision.DENY
    assert result.executed is False
    assert (contract, capability, policy, enforcement) == before


def test_scenario_prediction_is_order_invariant_for_three_permutations() -> None:
    baseline = SingleObservationBaseline()
    negative = baseline.evaluate(observation(request_id="a"), local_context())
    positive = baseline.evaluate(
        observation(request_id="b", resource="/outside/b", sequence_number=2),
        local_context(),
    )
    incomplete_context = TaskContext(
        "1", "task-a", TaskPurpose("report_delivery", CONTRACT_SOURCE)
    )
    abstain = baseline.evaluate(
        observation(
            request_id="c",
            action="network.send",
            resource="api:delivery",
            sequence_number=3,
        ),
        incomplete_context,
    )

    abc = baseline.aggregate([negative, positive, abstain])
    cba = baseline.aggregate([abstain, positive, negative])
    bac = baseline.aggregate([positive, negative, abstain])

    assert abc == cba == bac
    assert abc.prediction is BaselinePrediction.POSITIVE


def test_duplicate_observation_is_idempotent() -> None:
    baseline = SingleObservationBaseline()
    mismatch = baseline.evaluate(observation(resource="/outside/a"), local_context())

    once = baseline.aggregate([mismatch])
    repeated = baseline.aggregate([mismatch, mismatch, mismatch])

    assert once == repeated
    assert len(repeated.observation_results) == 1


def test_sequence_number_change_alone_cannot_change_prediction() -> None:
    baseline = SingleObservationBaseline()
    original = observation()
    renumbered = replace(original, sequence_number=999)

    first = baseline.evaluate(original, local_context())
    second = baseline.evaluate(renumbered, local_context())

    assert first.sequence_number != second.sequence_number
    assert first.prediction is second.prediction
    assert baseline.aggregate([first]).prediction is baseline.aggregate([second]).prediction


def test_classifier_has_no_scenario_category_or_trajectory_dependency() -> None:
    source = inspect.getsource(baseline_module)
    evaluate_parameters = inspect.signature(SingleObservationBaseline.evaluate).parameters

    assert "scenario_id" not in source
    assert "task_category" not in source
    assert "context_trajectory" not in source
    assert "CTXTRJ" not in source
    assert "scenario_id" not in evaluate_parameters
    assert "task_category" not in evaluate_parameters


def test_baseline_produces_no_trajectory_finding() -> None:
    result = SingleObservationBaseline().evaluate(observation(), local_context())

    assert isinstance(result, SingleObservationBaselineResult)
    assert not isinstance(result, TrajectoryFinding)
    assert not hasattr(result, "finding_id")
    assert not hasattr(result, "findings")


def test_all_individually_consistent_actions_do_not_create_history_signal() -> None:
    context = TaskContext(
        "1",
        "task-a",
        TaskPurpose("multi_stage_work", CONTRACT_SOURCE),
        resource_roles=(
            ResourceRole("stage:a", "stage_a", REGISTRY_SOURCE),
            ResourceRole("stage:b", "stage_b", REGISTRY_SOURCE),
            ResourceRole("stage:c", "stage_c", REGISTRY_SOURCE),
        ),
    )
    baseline = SingleObservationBaseline()
    results = [
        baseline.evaluate(
            observation(request_id=name, resource=f"stage:{name}", sequence_number=index),
            context,
        )
        for index, name in enumerate(("a", "b", "c"), start=1)
    ]

    assert {result.prediction for result in results} == {BaselinePrediction.NEGATIVE}
    assert baseline.aggregate(results).prediction is BaselinePrediction.NEGATIVE
    assert baseline.aggregate(reversed(results)).prediction is BaselinePrediction.NEGATIVE


def test_partial_stale_and_mismatching_context_behaviors_are_explicit() -> None:
    baseline = SingleObservationBaseline()
    partial = TaskContext(
        "1", "task-a", TaskPurpose("report_delivery", CONTRACT_SOURCE)
    )
    partial_result = baseline.evaluate(
        observation(action="network.send", resource="api:delivery"), partial
    )
    stale_but_matching = baseline.evaluate(
        observation(), local_context(source_reference="registry:roles:old")
    )
    mismatch = baseline.evaluate(observation(resource="/outside/a"), local_context())

    assert partial_result.prediction is BaselinePrediction.ABSTAIN
    assert stale_but_matching.prediction is BaselinePrediction.NEGATIVE
    assert "registry:roles:old" in {
        source.immutable_reference for source in stale_but_matching.context_sources
    }
    assert mismatch.prediction is BaselinePrediction.POSITIVE


def test_precomputed_evaluation_must_match_observation_binding() -> None:
    baseline = SingleObservationBaseline()
    item = observation()
    evaluation = ContextEvaluator().evaluate(item, local_context())

    with pytest.raises(ValueError, match="not bound"):
        baseline.classify(replace(item, request_id="other"), evaluation)


def test_scenario_reduction_abstains_only_without_positive_evidence() -> None:
    baseline = SingleObservationBaseline()
    negative = baseline.evaluate(observation(), local_context())
    incomplete = TaskContext(
        "1", "task-a", TaskPurpose("report_delivery", CONTRACT_SOURCE)
    )
    abstain = baseline.evaluate(
        observation(request_id="request-b", action="network.send", resource="api:x"),
        incomplete,
    )

    scenario = baseline.aggregate([negative, abstain])

    assert isinstance(scenario, SingleObservationScenarioResult)
    assert scenario.prediction is BaselinePrediction.ABSTAIN


def test_scenario_reduction_rejects_empty_or_cross_scenario_inputs() -> None:
    baseline = SingleObservationBaseline()
    first = baseline.evaluate(observation(), local_context())
    other_session = replace(first, session_id="session-b")
    other_baseline = replace(first, baseline_id="other-baseline")

    with pytest.raises(ValueError, match="at least one"):
        baseline.aggregate([])
    with pytest.raises(ValueError, match="baseline identifier"):
        baseline.aggregate([other_baseline])
    with pytest.raises(ValueError, match="share one"):
        baseline.aggregate([first, other_session])
