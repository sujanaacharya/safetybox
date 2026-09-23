"""SafetyBox deterministic reference-monitor and task-capability kernel."""

from safetybox.capabilities import Capability, CapabilityEvaluator, resource_matches
from safetybox.contracts import TaskContract
from safetybox.exceptions import AuthorizationFailure
from safetybox.models import ActionRequest, Decision, EnforcementResult, PolicyDecision
from safetybox.monitor import ReferenceMonitor
from safetybox.policy import StaticPolicy, TaskContractPolicy

__all__ = [
    "ActionRequest",
    "AuthorizationFailure",
    "Capability",
    "CapabilityEvaluator",
    "Decision",
    "EnforcementResult",
    "PolicyDecision",
    "ReferenceMonitor",
    "StaticPolicy",
    "TaskContract",
    "TaskContractPolicy",
    "resource_matches",
]
