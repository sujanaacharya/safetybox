"""Immutable scenario definitions and evidence records for M4."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

from safetybox.contracts import TaskContract
from safetybox.events import SafetyBoxEvent
from safetybox.models import Decision
from safetybox.simulation.tools import SimulatedWorldSnapshot


def _immutable_mapping(values: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType(dict(values))


class ExecutionExpectation(StrEnum):
    """The expected policy/execution outcome for one scenario step."""

    MUST_EXECUTE = "MUST_EXECUTE"
    MUST_NOT_EXECUTE = "MUST_NOT_EXECUTE"
    OBSERVATION_ONLY = "OBSERVATION_ONLY"


@dataclass(frozen=True, slots=True)
class ScenarioStep:
    """One ordered, scenario-facing attempted action.

    ``request_task_id`` permits a controlled task-binding mismatch without
    requiring scenario authors to construct an internal ``ActionRequest``.
    """

    step_id: str
    actor: str
    action: str
    resource: str
    arguments: Mapping[str, object] = field(default_factory=dict)
    request_task_id: str | None = None

    def __post_init__(self) -> None:
        if not all((self.step_id, self.actor, self.action, self.resource)):
            raise ValueError("Scenario step identifiers, actor, action, and resource are required.")
        object.__setattr__(self, "arguments", _immutable_mapping(self.arguments))


@dataclass(frozen=True, slots=True)
class StepExpectation:
    """A precise, evaluable expected execution property for a step."""

    step_id: str
    expectation: ExecutionExpectation


@dataclass(frozen=True, slots=True)
class ScenarioExpectation:
    """Scenario security property plus explicit step-level observations.

    ``CURRENTLY_UNDETECTABLE`` is intentionally a descriptive status, not a
    passing security verdict. It identifies scenarios retained for a future
    detector even when M4's action-level policy permits every step.
    """

    expected_security_property: str
    step_expectations: tuple[StepExpectation, ...] = ()
    current_status: str = "PARTIALLY_ENFORCED"

    def __init__(
        self,
        expected_security_property: str,
        step_expectations: Iterable[StepExpectation] = (),
        current_status: str = "PARTIALLY_ENFORCED",
    ) -> None:
        if not expected_security_property:
            raise ValueError("Scenario expected_security_property must not be empty.")
        object.__setattr__(self, "expected_security_property", expected_security_property)
        object.__setattr__(self, "step_expectations", tuple(step_expectations))
        object.__setattr__(self, "current_status", current_status)


@dataclass(frozen=True, slots=True)
class ThreatScenario:
    """Reusable immutable scenario definition with no runtime state."""

    scenario_id: str
    title: str
    description: str
    threat_category: str
    task_contract: TaskContract
    steps: tuple[ScenarioStep, ...]
    expectation: ScenarioExpectation
    research_questions: tuple[str, ...] = ()
    hypotheses: tuple[str, ...] = ()
    notes: str = ""

    def __init__(
        self,
        scenario_id: str,
        title: str,
        description: str,
        threat_category: str,
        task_contract: TaskContract,
        steps: Iterable[ScenarioStep],
        expectation: ScenarioExpectation,
        research_questions: Iterable[str] = (),
        hypotheses: Iterable[str] = (),
        notes: str = "",
    ) -> None:
        materialized_steps = tuple(steps)
        if not all((scenario_id, title, description, threat_category)):
            raise ValueError("Scenario identity, title, description, and category are required.")
        if not materialized_steps:
            raise ValueError("A scenario must contain at least one step.")
        step_ids = tuple(step.step_id for step in materialized_steps)
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("Scenario step IDs must be unique.")
        expectation_ids = tuple(item.step_id for item in expectation.step_expectations)
        if (
            len(expectation_ids) != len(set(expectation_ids))
            or not set(expectation_ids) <= set(step_ids)
        ):
            raise ValueError("Step expectations must refer to unique scenario step IDs.")
        object.__setattr__(self, "scenario_id", scenario_id)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "threat_category", threat_category)
        object.__setattr__(self, "task_contract", task_contract)
        object.__setattr__(self, "steps", materialized_steps)
        object.__setattr__(self, "expectation", expectation)
        object.__setattr__(self, "research_questions", tuple(research_questions))
        object.__setattr__(self, "hypotheses", tuple(hypotheses))
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class StepResult:
    """Immutable raw evidence for one attempted scenario step."""

    step_id: str
    request_id: str
    policy_decision: Decision
    rule_id: str
    executed: bool
    tool_effect_observed: bool
    correlation_id: str


@dataclass(frozen=True, slots=True)
class SecurityExpectationResult:
    """Data-only evaluation of one declared step expectation."""

    step_id: str
    expectation: ExecutionExpectation
    observed_executed: bool
    satisfied: bool


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    """Immutable evidence from one complete scenario run."""

    scenario_id: str
    task_contract: TaskContract
    expected_security_property: str
    current_status: str
    step_results: tuple[StepResult, ...]
    audit_events: tuple[SafetyBoxEvent, ...]
    security_expectation_results: tuple[SecurityExpectationResult, ...]
    world_snapshot: SimulatedWorldSnapshot

    @property
    def attempted_steps(self) -> int:
        return len(self.step_results)

    @property
    def executed_count(self) -> int:
        return sum(result.executed for result in self.step_results)

    @property
    def blocked_count(self) -> int:
        return self.attempted_steps - self.executed_count

    @property
    def expectations_satisfied(self) -> int:
        return sum(result.satisfied for result in self.security_expectation_results)

    @property
    def expectations_failed(self) -> int:
        return len(self.security_expectation_results) - self.expectations_satisfied
