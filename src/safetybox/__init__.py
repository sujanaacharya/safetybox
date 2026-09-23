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

__all__ = [
    "ActionRequest",
    "AuditFailure",
    "AuditRecorder",
    "AuditSink",
    "AuthorizationFailure",
    "Capability",
    "CapabilityEvaluator",
    "Decision",
    "EnforcementResult",
    "EventType",
    "InMemoryAuditSink",
    "PolicyDecision",
    "ReferenceMonitor",
    "StaticPolicy",
    "SafetyBoxEvent",
    "TaskContract",
    "TaskContractPolicy",
    "resource_matches",
]
