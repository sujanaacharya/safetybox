"""SafetyBox deterministic reference-monitor and task-capability kernel."""

from safetybox.audit import AuditRecorder, InMemoryAuditSink
from safetybox.capabilities import Capability, CapabilityEvaluator, resource_matches
from safetybox.contracts import TaskContract
from safetybox.events import EventType, SafetyBoxEvent
from safetybox.exceptions import AuditFailure, AuthorizationFailure
from safetybox.models import ActionRequest, Decision, EnforcementResult, PolicyDecision
from safetybox.monitor import ReferenceMonitor
from safetybox.policy import StaticPolicy, TaskContractPolicy
from safetybox.protocols import AuditSink
from safetybox.simulation import (
    BENIGN_001,
    BENIGN_002,
    INITIAL_SCENARIOS,
    TS_001,
    TS_006,
    TS_008,
    TS_009,
    TS_010,
    ExecutionExpectation,
    ScenarioExpectation,
    ScenarioResult,
    ScenarioRunner,
    ScenarioStep,
    SecurityExpectationResult,
    SimulatedWorld,
    SimulatedWorldSnapshot,
    SimulationInfrastructureError,
    StepExpectation,
    StepResult,
    ThreatScenario,
)

__all__ = [
    "ActionRequest",
    "AuditFailure",
    "AuditRecorder",
    "AuditSink",
    "BENIGN_001",
    "BENIGN_002",
    "AuthorizationFailure",
    "Capability",
    "CapabilityEvaluator",
    "Decision",
    "EnforcementResult",
    "ExecutionExpectation",
    "EventType",
    "InMemoryAuditSink",
    "INITIAL_SCENARIOS",
    "PolicyDecision",
    "ReferenceMonitor",
    "ScenarioExpectation",
    "ScenarioResult",
    "ScenarioRunner",
    "ScenarioStep",
    "SecurityExpectationResult",
    "SimulatedWorld",
    "SimulatedWorldSnapshot",
    "SimulationInfrastructureError",
    "StaticPolicy",
    "SafetyBoxEvent",
    "TaskContract",
    "TaskContractPolicy",
    "StepExpectation",
    "StepResult",
    "ThreatScenario",
    "TS_001",
    "TS_006",
    "TS_008",
    "TS_009",
    "TS_010",
    "resource_matches",
]
