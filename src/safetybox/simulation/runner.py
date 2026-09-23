"""Deterministic orchestration of scenarios through the existing M1--M3 seam."""

from __future__ import annotations

from dataclasses import dataclass

from safetybox.audit import AuditRecorder, InMemoryAuditSink
from safetybox.models import ActionRequest
from safetybox.monitor import ReferenceMonitor
from safetybox.policy import TaskContractPolicy
from safetybox.simulation.models import (
    ExecutionExpectation,
    ScenarioResult,
    SecurityExpectationResult,
    StepResult,
    ThreatScenario,
)
from safetybox.simulation.tools import SimulatedTool, SimulatedWorld


class SimulationInfrastructureError(RuntimeError):
    """A malformed scenario or broken simulator, distinct from a failed expectation."""


@dataclass(frozen=True, slots=True)
class ScenarioRunner:
    """Run one scenario with fresh deterministic in-memory components."""

    session_prefix: str = "simulation"

    def run(self, scenario: ThreatScenario) -> ScenarioResult:
        world = SimulatedWorld()
        sink = InMemoryAuditSink()
        monitor = ReferenceMonitor(
            TaskContractPolicy(scenario.task_contract),
            SimulatedTool(world),
            AuditRecorder(sink),
        )
        results: list[StepResult] = []
        for step in scenario.steps:
            request = ActionRequest(
                request_id=f"{scenario.scenario_id}:{step.step_id}",
                session_id=f"{self.session_prefix}:{scenario.scenario_id}",
                task_id=step.request_task_id or scenario.task_contract.task_id,
                actor=step.actor,
                action=step.action,
                resource=step.resource,
                arguments=step.arguments,
            )
            before_effects = world.snapshot()
            try:
                enforcement = monitor.execute(request)
            except Exception as error:
                raise SimulationInfrastructureError(
                    f"Scenario {scenario.scenario_id} failed at {step.step_id}."
                ) from error
            after_effects = world.snapshot()
            results.append(
                StepResult(
                    step_id=step.step_id,
                    request_id=request.request_id,
                    policy_decision=enforcement.policy_decision.decision,
                    rule_id=enforcement.policy_decision.rule_id,
                    executed=enforcement.executed,
                    tool_effect_observed=before_effects != after_effects,
                    correlation_id=enforcement.correlation_id or request.request_id,
                )
            )
        expectation_results = self._evaluate(scenario, tuple(results))
        return ScenarioResult(
            scenario_id=scenario.scenario_id,
            task_contract=scenario.task_contract,
            expected_security_property=scenario.expectation.expected_security_property,
            current_status=scenario.expectation.current_status,
            step_results=tuple(results),
            audit_events=sink.events(),
            security_expectation_results=expectation_results,
            world_snapshot=world.snapshot(),
        )

    @staticmethod
    def _evaluate(
        scenario: ThreatScenario, results: tuple[StepResult, ...]
    ) -> tuple[SecurityExpectationResult, ...]:
        by_step_id = {result.step_id: result for result in results}
        evaluated: list[SecurityExpectationResult] = []
        for expected in scenario.expectation.step_expectations:
            observed = by_step_id[expected.step_id].executed
            satisfied = (
                expected.expectation is ExecutionExpectation.OBSERVATION_ONLY
                or observed == (expected.expectation is ExecutionExpectation.MUST_EXECUTE)
            )
            evaluated.append(
                SecurityExpectationResult(
                    step_id=expected.step_id,
                    expectation=expected.expectation,
                    observed_executed=observed,
                    satisfied=satisfied,
                )
            )
        return tuple(evaluated)
