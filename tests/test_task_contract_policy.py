"""Executable M2 evidence for task-scoped capability enforcement."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass, field

import pytest

from safetybox import (
    ActionRequest,
    Capability,
    Decision,
    PolicyDecision,
    ReferenceMonitor,
    TaskContract,
    TaskContractPolicy,
)


def request(*, task_id: str = "task-a", action: str, resource: str) -> ActionRequest:
    return ActionRequest("request-1", "session-1", task_id, "test-agent", action, resource)


@dataclass
class RecordingTool:
    operations: list[str] = field(default_factory=list)
    requests: list[ActionRequest] = field(default_factory=list)

    def execute(self, action_request: ActionRequest) -> object:
        self.operations.append("execute")
        self.requests.append(action_request)
        return "executed"


def monitor_for(*capabilities: Capability) -> tuple[ReferenceMonitor, RecordingTool]:
    tool = RecordingTool()
    contract = TaskContract("task-a", "test task", capabilities)
    return ReferenceMonitor(TaskContractPolicy(contract), tool), tool


def test_exact_action_resource_capability_allows_and_forwards() -> None:
    monitor, tool = monitor_for(Capability("database.query", "db:analytics"))

    result = monitor.execute(request(action="database.query", resource="db:analytics"))

    assert result.policy_decision.decision is Decision.ALLOW
    assert result.policy_decision.rule_id == "POL-M2-CAPABILITY-ALLOW"
    assert result.executed is True
    assert tool.requests == [result.request]


def test_missing_action_capability_denies_without_execution() -> None:
    monitor, tool = monitor_for(Capability("filesystem.read", "/workspace/project/**"))

    result = monitor.execute(
        request(action="filesystem.write", resource="/workspace/project/a.txt")
    )

    assert result.policy_decision.rule_id == "POL-M2-CAPABILITY-MISSING"
    assert result.executed is False
    assert tool.requests == []


def test_out_of_scope_resource_denies_without_execution() -> None:
    monitor, tool = monitor_for(Capability("filesystem.read", "/workspace/project/**"))

    result = monitor.execute(request(action="filesystem.read", resource="/workspace/other/file.py"))

    assert result.policy_decision.rule_id == "POL-M2-RESOURCE-OUT-OF-SCOPE"
    assert result.executed is False
    assert tool.requests == []


def test_nested_resource_in_scope_is_allowed() -> None:
    monitor, tool = monitor_for(Capability("filesystem.read", "/workspace/project/**"))

    result = monitor.execute(
        request(action="filesystem.read", resource="/workspace/project/src/module.py")
    )

    assert result.executed is True
    assert len(tool.requests) == 1


def test_prefix_confusion_is_denied_without_execution() -> None:
    monitor, tool = monitor_for(Capability("filesystem.read", "/workspace/project/**"))

    result = monitor.execute(
        request(action="filesystem.read", resource="/workspace/project-secret/key.txt")
    )

    assert result.policy_decision.rule_id == "POL-M2-RESOURCE-OUT-OF-SCOPE"
    assert tool.requests == []


def test_task_mismatch_denies_without_execution() -> None:
    monitor, tool = monitor_for(Capability("database.query", "db:analytics"))

    result = monitor.execute(
        request(task_id="task-b", action="database.query", resource="db:analytics")
    )

    assert result.policy_decision.rule_id == "POL-M2-TASK-MISMATCH"
    assert result.executed is False
    assert tool.requests == []


def test_empty_contract_defaults_to_deny() -> None:
    monitor, tool = monitor_for()

    result = monitor.execute(request(action="database.query", resource="db:analytics"))

    assert result.policy_decision.decision is Decision.DENY
    assert result.policy_decision.rule_id == "POL-M2-CAPABILITY-MISSING"
    assert tool.requests == []


def test_contract_capabilities_are_copied_and_immutable() -> None:
    supplied = [Capability("filesystem.read", "/workspace/project/**")]
    contract = TaskContract("task-a", "test task", supplied)
    supplied.append(Capability("filesystem.write", "/workspace/project/**"))

    assert contract.capabilities == {Capability("filesystem.read", "/workspace/project/**")}
    with pytest.raises(FrozenInstanceError):
        contract.task_id = "task-b"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        contract.capabilities.add(Capability("filesystem.write", "/workspace/project/**"))


def test_same_action_different_resource_scopes_do_not_broaden_authority() -> None:
    monitor, tool = monitor_for(
        Capability("filesystem.read", "/workspace/project/**"),
        Capability("filesystem.read", "/workspace/input/**"),
    )

    result = monitor.execute(
        request(action="filesystem.read", resource="/workspace/secrets/key.txt")
    )

    assert result.policy_decision.rule_id == "POL-M2-RESOURCE-OUT-OF-SCOPE"
    assert tool.requests == []


def test_same_resource_different_action_does_not_grant_write() -> None:
    monitor, tool = monitor_for(Capability("filesystem.read", "/workspace/project/report.txt"))

    result = monitor.execute(
        request(action="filesystem.write", resource="/workspace/project/report.txt")
    )

    assert result.policy_decision.rule_id == "POL-M2-CAPABILITY-MISSING"
    assert tool.requests == []


def test_task_contract_policy_authorizes_before_tool_execution() -> None:
    operations: list[str] = []
    contract = TaskContract("task-a", "test task", [Capability("database.query", "db:analytics")])

    @dataclass
    class RecordingPolicy:
        policy: TaskContractPolicy

        def authorize(self, action_request: ActionRequest) -> PolicyDecision:
            operations.append("authorize")
            return self.policy.authorize(action_request)

    tool = RecordingTool(operations)
    result = ReferenceMonitor(RecordingPolicy(TaskContractPolicy(contract)), tool).execute(
        request(action="database.query", resource="db:analytics")
    )

    assert result.executed is True
    assert operations == ["authorize", "execute"]
