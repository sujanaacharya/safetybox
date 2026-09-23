"""Executable M1 evidence for the in-process reference-monitor boundary."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from safetybox import (
    ActionRequest,
    AuthorizationFailure,
    Decision,
    PolicyDecision,
    ReferenceMonitor,
    StaticPolicy,
)


def request(*, action: str = "document.read", resource: str = "report.txt") -> ActionRequest:
    return ActionRequest(
        request_id="request-1",
        session_id="session-1",
        task_id="task-1",
        actor="test-agent",
        action=action,
        resource=resource,
        arguments={"format": "text"},
    )


@dataclass
class RecordingTool:
    operations: list[str] = field(default_factory=list)
    requests: list[ActionRequest] = field(default_factory=list)

    def execute(self, action_request: ActionRequest) -> object:
        self.operations.append("execute")
        self.requests.append(action_request)
        return {"received_request_id": action_request.request_id}

    @property
    def execution_count(self) -> int:
        return len(self.requests)


@dataclass
class RecordingAuthorizer:
    policy_decision: PolicyDecision
    operations: list[str] = field(default_factory=list)
    requests: list[ActionRequest] = field(default_factory=list)

    def authorize(self, action_request: ActionRequest) -> PolicyDecision:
        self.operations.append("authorize")
        self.requests.append(action_request)
        return self.policy_decision


def test_allowed_action_is_authorized_then_forwarded() -> None:
    action_request = request()
    authorizer = RecordingAuthorizer(PolicyDecision(Decision.ALLOW, "POL-TEST-ALLOW", "allowed"))
    tool = RecordingTool()

    result = ReferenceMonitor(authorizer, tool).execute(action_request)

    assert authorizer.requests == [action_request]
    assert tool.execution_count == 1
    assert tool.requests == [action_request]
    assert result.executed is True
    assert result.tool_result == {"received_request_id": "request-1"}


def test_denied_action_never_reaches_protected_tool_and_preserves_decision() -> None:
    action_request = request()
    decision = PolicyDecision(Decision.DENY, "POL-TEST-DENY", "test denial")
    authorizer = RecordingAuthorizer(decision)
    tool = RecordingTool()

    result = ReferenceMonitor(authorizer, tool).execute(action_request)

    assert authorizer.requests == [action_request]
    assert tool.execution_count == 0
    assert tool.requests == []
    assert result.executed is False
    assert result.policy_decision.rule_id == "POL-TEST-DENY"
    assert result.policy_decision.reason == "test denial"


def test_authorization_completes_before_execution() -> None:
    operations: list[str] = []
    decision = PolicyDecision(Decision.ALLOW, "POL-TEST-ALLOW", "allowed")
    authorizer = RecordingAuthorizer(decision, operations)
    tool = RecordingTool(operations)

    ReferenceMonitor(authorizer, tool).execute(request())

    assert operations == ["authorize", "execute"]


def test_static_policy_defaults_to_deny_without_execution() -> None:
    tool = RecordingTool()
    result = ReferenceMonitor(StaticPolicy(), tool).execute(request())

    assert result.policy_decision.decision is Decision.DENY
    assert result.policy_decision.rule_id == "POL-M1-DEFAULT-DENY"
    assert result.executed is False
    assert tool.execution_count == 0


def test_authorization_failure_fails_closed_without_tool_invocation() -> None:
    class FailingAuthorizer:
        def authorize(self, action_request: ActionRequest) -> PolicyDecision:
            raise RuntimeError("policy unavailable")

    tool = RecordingTool()

    with pytest.raises(AuthorizationFailure, match="Authorization failed") as failure:
        ReferenceMonitor(FailingAuthorizer(), tool).execute(request())

    assert isinstance(failure.value.__cause__, RuntimeError)
    assert tool.execution_count == 0


def test_multiple_denied_requests_never_reach_protected_tool() -> None:
    tool = RecordingTool()
    monitor = ReferenceMonitor(StaticPolicy(), tool)

    results = [
        monitor.execute(request(action="document.write", resource="report.txt")),
        monitor.execute(request(action="shell.execute", resource="dangerous-command")),
        monitor.execute(request(action="network.connect", resource="example.invalid")),
    ]

    assert all(result.executed is False for result in results)
    assert tool.execution_count == 0


def test_policy_decision_metadata_is_preserved_in_enforcement_result() -> None:
    metadata = {"policy_version": "m1-test", "priority": 1}
    decision = PolicyDecision(Decision.DENY, "POL-TEST-METADATA", "metadata retained", metadata)
    tool = RecordingTool()

    result = ReferenceMonitor(RecordingAuthorizer(decision), tool).execute(request())

    assert result.policy_decision.rule_id == "POL-TEST-METADATA"
    assert result.policy_decision.reason == "metadata retained"
    assert result.policy_decision.metadata == metadata
    assert tool.execution_count == 0
