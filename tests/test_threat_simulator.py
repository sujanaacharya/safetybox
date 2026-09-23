"""Executable M4 evidence for deterministic, harmless threat simulation."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from safetybox import (
    BENIGN_001,
    TS_001,
    TS_006,
    TS_008,
    TS_009,
    Capability,
    Decision,
    ExecutionExpectation,
    ScenarioExpectation,
    ScenarioRunner,
    ScenarioStep,
    SimulationInfrastructureError,
    StepExpectation,
    TaskContract,
    ThreatScenario,
)


def test_ts_001_allows_permitted_file_read_and_blocks_logical_credential() -> None:
    result = ScenarioRunner().run(TS_001)

    allowed, denied = result.step_results
    assert allowed.policy_decision is Decision.ALLOW
    assert allowed.executed is True
    assert denied.policy_decision is Decision.DENY
    assert denied.executed is False
    assert result.world_snapshot.files_read == ("/workspace/project/src/app.py",)
    assert result.task_contract == TS_001.task_contract
    assert result.expected_security_property == TS_001.expectation.expected_security_property


def test_blocked_operation_causes_no_simulated_side_effect() -> None:
    result = ScenarioRunner().run(TS_001)

    assert result.step_results[1].tool_effect_observed is False
    assert "secret:developer_credential" not in result.world_snapshot.files_read


def test_ts_006_cross_task_request_is_denied_without_effect() -> None:
    result = ScenarioRunner().run(TS_006)

    assert result.step_results[0].rule_id == "POL-M2-TASK-MISMATCH"
    assert result.step_results[0].executed is False
    assert result.world_snapshot.database_queries == ()


def test_ts_008_boundary_probing_produces_no_forbidden_effects() -> None:
    result = ScenarioRunner().run(TS_008)

    assert result.executed_count == 0
    assert result.blocked_count == 3
    assert result.world_snapshot.files_read == ()


def test_ts_009_permits_individually_allowed_trajectory_actions() -> None:
    result = ScenarioRunner().run(TS_009)

    assert result.executed_count == 4
    assert result.blocked_count == 0
    assert result.world_snapshot.network_requests == ("network:approved-reporting-endpoint",)
    assert result.expectations_failed == 0


def test_benign_control_completes_without_unnecessary_blocking() -> None:
    result = ScenarioRunner().run(BENIGN_001)

    assert result.executed_count == result.attempted_steps
    assert result.blocked_count == 0


def test_result_preserves_blocked_and_executed_counts() -> None:
    result = ScenarioRunner().run(TS_001)

    assert result.attempted_steps == 2
    assert result.executed_count == 1
    assert result.blocked_count == 1
    assert result.expectations_satisfied == 2


def test_each_step_correlates_to_its_m3_audit_events() -> None:
    result = ScenarioRunner().run(TS_001)

    for step in result.step_results:
        events = [event for event in result.audit_events if event.request_id == step.request_id]
        assert events
        assert {event.correlation_id for event in events} == {step.correlation_id}
        assert {event.task_id for event in events} == {"task-ts-001"}


def test_repeated_runs_have_equivalent_semantic_outcomes() -> None:
    first = ScenarioRunner().run(TS_009)
    second = ScenarioRunner().run(TS_009)

    assert [
        (item.step_id, item.policy_decision, item.rule_id, item.executed, item.tool_effect_observed)
        for item in first.step_results
    ] == [
        (item.step_id, item.policy_decision, item.rule_id, item.executed, item.tool_effect_observed)
        for item in second.step_results
    ]
    assert [event.event_type for event in first.audit_events] == [
        event.event_type for event in second.audit_events
    ]


def test_scenario_definition_and_result_evidence_are_immutable() -> None:
    result = ScenarioRunner().run(TS_001)

    with pytest.raises(FrozenInstanceError):
        TS_001.title = "changed"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        TS_001.steps.append(TS_001.steps[0])  # type: ignore[attr-defined]
    with pytest.raises(FrozenInstanceError):
        result.step_results[0].executed = False  # type: ignore[misc]
    with pytest.raises(AttributeError):
        result.audit_events.append(result.audit_events[0])  # type: ignore[attr-defined]


def test_security_expectation_failure_is_data_not_a_simulator_crash() -> None:
    scenario = ThreatScenario(
        "TEST-EXPECTATION-FAILURE",
        "Expectation mismatch",
        "An allowed action intentionally contradicts its declared expectation.",
        "test",
        TaskContract("test-task", "test", [Capability("filesystem.read", "/workspace/project/**")]),
        [ScenarioStep("step-01", "scenario-agent", "filesystem.read", "/workspace/project/a.py")],
        ScenarioExpectation(
            "This intentionally fails as experimental evidence.",
            [StepExpectation("step-01", ExecutionExpectation.MUST_NOT_EXECUTE)],
        ),
    )

    result = ScenarioRunner().run(scenario)

    assert result.step_results[0].executed is True
    assert result.expectations_failed == 1
    assert result.security_expectation_results[0].satisfied is False


def test_broken_simulator_configuration_is_distinguished_from_security_failure() -> None:
    scenario = ThreatScenario(
        "TEST-INFRASTRUCTURE-FAILURE",
        "Unsupported simulated action",
        "A granted action with no simulated adapter is malformed M4 configuration.",
        "test",
        TaskContract("test-task", "test", [Capability("unsupported.action", "logical:resource")]),
        [ScenarioStep("step-01", "scenario-agent", "unsupported.action", "logical:resource")],
        ScenarioExpectation("No result should be produced for an invalid simulator configuration."),
    )

    with pytest.raises(SimulationInfrastructureError):
        ScenarioRunner().run(scenario)
