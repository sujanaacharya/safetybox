"""Executable M3 evidence for ordered ReferenceMonitor audit events."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass

import pytest

from safetybox import (
    ActionRequest,
    AuditFailure,
    AuditRecorder,
    AuthorizationFailure,
    Decision,
    EventType,
    InMemoryAuditSink,
    PolicyDecision,
    ReferenceMonitor,
)
from safetybox.events import SafetyBoxEvent


def request(
    request_id: str = "request-1", session_id: str = "session-1", task_id: str = "task-1"
) -> ActionRequest:
    return ActionRequest(
        request_id, session_id, task_id, "test-agent", "document.read", "report.txt"
    )


@dataclass
class Tool:
    calls: int = 0
    failure: Exception | None = None

    def execute(self, action_request: ActionRequest) -> object:
        self.calls += 1
        if self.failure is not None:
            raise self.failure
        return "tool-result"


@dataclass
class Authorizer:
    result: PolicyDecision | None = None
    failure: Exception | None = None

    def authorize(self, action_request: ActionRequest) -> PolicyDecision:
        if self.failure is not None:
            raise self.failure
        assert self.result is not None
        return self.result


def monitor(authorizer: Authorizer, tool: Tool, sink: InMemoryAuditSink) -> ReferenceMonitor:
    return ReferenceMonitor(authorizer, tool, AuditRecorder(sink))


def event_types(sink: InMemoryAuditSink) -> list[EventType]:
    return [event.event_type for event in sink.events()]


def test_allowed_flow_is_complete_ordered_and_attributable() -> None:
    sink = InMemoryAuditSink()
    tool = Tool()
    action_request = request()
    result = monitor(
        Authorizer(PolicyDecision(Decision.ALLOW, "POL-ALLOW", "allowed")), tool, sink
    ).execute(action_request)

    events = sink.events()
    assert event_types(sink) == [
        EventType.ACTION_REQUESTED,
        EventType.AUTHORIZATION_STARTED,
        EventType.AUTHORIZATION_ALLOWED,
        EventType.EXECUTION_STARTED,
        EventType.EXECUTION_SUCCEEDED,
    ]
    assert [event.sequence_number for event in events] == [1, 2, 3, 4, 5]
    assert {event.session_id for event in events} == {action_request.session_id}
    assert {event.task_id for event in events} == {action_request.task_id}
    assert {event.request_id for event in events} == {action_request.request_id}
    assert events[2].rule_id == "POL-ALLOW"
    assert events[2].decision is Decision.ALLOW
    assert events[3].parent_event_id == events[2].event_id
    assert events[4].parent_event_id == events[3].event_id
    assert result.correlation_id == action_request.request_id
    assert tool.calls == 1


def test_denial_is_distinct_and_never_starts_execution() -> None:
    sink = InMemoryAuditSink()
    tool = Tool()
    result = monitor(
        Authorizer(PolicyDecision(Decision.DENY, "POL-DENY", "denied")), tool, sink
    ).execute(request())

    assert event_types(sink) == [
        EventType.ACTION_REQUESTED,
        EventType.AUTHORIZATION_STARTED,
        EventType.AUTHORIZATION_DENIED,
    ]
    assert sink.events()[-1].rule_id == "POL-DENY"
    assert result.executed is False
    assert tool.calls == 0


def test_authorization_failure_is_distinct_and_fails_closed() -> None:
    sink = InMemoryAuditSink()
    tool = Tool()

    with pytest.raises(AuthorizationFailure):
        monitor(Authorizer(failure=RuntimeError("unavailable")), tool, sink).execute(request())

    assert event_types(sink) == [
        EventType.ACTION_REQUESTED,
        EventType.AUTHORIZATION_STARTED,
        EventType.AUTHORIZATION_FAILED,
    ]
    assert tool.calls == 0


def test_tool_failure_is_not_mislabeled_as_denial() -> None:
    sink = InMemoryAuditSink()
    tool = Tool(failure=ValueError("tool failed"))

    with pytest.raises(ValueError, match="tool failed"):
        monitor(
            Authorizer(PolicyDecision(Decision.ALLOW, "POL-ALLOW", "allowed")), tool, sink
        ).execute(request())

    assert event_types(sink) == [
        EventType.ACTION_REQUESTED,
        EventType.AUTHORIZATION_STARTED,
        EventType.AUTHORIZATION_ALLOWED,
        EventType.EXECUTION_STARTED,
        EventType.EXECUTION_FAILED,
    ]
    assert sink.events()[-1].decision is Decision.ALLOW
    assert tool.calls == 1


def test_sequence_is_unique_strict_and_session_local() -> None:
    sink = InMemoryAuditSink()
    shared_monitor = monitor(
        Authorizer(PolicyDecision(Decision.DENY, "POL-DENY", "denied")), Tool(), sink
    )
    shared_monitor.execute(request("request-1", "session-a"))
    shared_monitor.execute(request("request-2", "session-a"))
    shared_monitor.execute(request("request-3", "session-b"))

    a_numbers = [
        event.sequence_number for event in sink.events() if event.session_id == "session-a"
    ]
    b_numbers = [
        event.sequence_number for event in sink.events() if event.session_id == "session-b"
    ]
    assert a_numbers == [1, 2, 3, 4, 5, 6]
    assert len(a_numbers) == len(set(a_numbers))
    assert b_numbers == [1, 2, 3]
    assert len(b_numbers) == len(set(b_numbers))


def test_each_request_has_an_isolated_correlation_in_a_shared_session() -> None:
    sink = InMemoryAuditSink()
    shared_monitor = monitor(
        Authorizer(PolicyDecision(Decision.DENY, "POL-DENY", "denied")), Tool(), sink
    )
    shared_monitor.execute(request("request-a"))
    shared_monitor.execute(request("request-b"))

    first = [event for event in sink.events() if event.request_id == "request-a"]
    second = [event for event in sink.events() if event.request_id == "request-b"]
    assert {event.correlation_id for event in first} == {"request-a"}
    assert {event.correlation_id for event in second} == {"request-b"}


def test_audit_failure_before_execution_fails_closed() -> None:
    @dataclass
    class FailingSink:
        calls: int = 0

        def record(self, event: SafetyBoxEvent) -> None:
            self.calls += 1
            raise OSError("audit unavailable")

    tool = Tool()
    failing_sink = FailingSink()
    with pytest.raises(AuditFailure, match="Audit recording failed"):
        ReferenceMonitor(
            Authorizer(PolicyDecision(Decision.ALLOW, "POL-ALLOW", "allowed")),
            tool,
            AuditRecorder(failing_sink),
        ).execute(request())

    assert failing_sink.calls == 1
    assert tool.calls == 0


def test_terminal_audit_failure_cannot_undo_an_already_executed_action() -> None:
    @dataclass
    class FailingTerminalSink:
        calls: int = 0

        def record(self, event: SafetyBoxEvent) -> None:
            self.calls += 1
            if self.calls == 5:
                raise OSError("audit unavailable")

    tool = Tool()
    with pytest.raises(AuditFailure, match="execution status may be indeterminate"):
        ReferenceMonitor(
            Authorizer(PolicyDecision(Decision.ALLOW, "POL-ALLOW", "allowed")),
            tool,
            AuditRecorder(FailingTerminalSink()),
        ).execute(request())

    assert tool.calls == 1


def test_events_and_sink_snapshots_are_immutable() -> None:
    sink = InMemoryAuditSink()
    monitor(Authorizer(PolicyDecision(Decision.DENY, "POL-DENY", "denied")), Tool(), sink).execute(
        request()
    )
    event = sink.events()[0]

    with pytest.raises(FrozenInstanceError):
        event.sequence_number = 99  # type: ignore[misc]
    with pytest.raises(TypeError):
        event.metadata["new"] = "value"  # type: ignore[index]
    with pytest.raises(AttributeError):
        sink.events().append(event)  # type: ignore[attr-defined]


def test_default_monitor_events_remain_semantically_m3_compatible() -> None:
    sink = InMemoryAuditSink()
    action_request = request()
    result = monitor(
        Authorizer(PolicyDecision(Decision.ALLOW, "POL-ALLOW", "allowed")),
        Tool(),
        sink,
    ).execute(action_request)

    normalized = [
        (
            event.event_type.value,
            event.session_id,
            event.task_id,
            event.request_id,
            event.action,
            event.resource,
            event.rule_id,
            None if event.decision is None else event.decision.value,
            event.executed,
            dict(event.metadata),
        )
        for event in sink.events()
    ]
    assert normalized == [
        (
            "ACTION_REQUESTED",
            "session-1",
            "task-1",
            "request-1",
            "document.read",
            "report.txt",
            None,
            None,
            None,
            {},
        ),
        (
            "AUTHORIZATION_STARTED",
            "session-1",
            "task-1",
            "request-1",
            "document.read",
            "report.txt",
            None,
            None,
            None,
            {},
        ),
        (
            "AUTHORIZATION_ALLOWED",
            "session-1",
            "task-1",
            "request-1",
            "document.read",
            "report.txt",
            "POL-ALLOW",
            "ALLOW",
            False,
            {},
        ),
        (
            "EXECUTION_STARTED",
            "session-1",
            "task-1",
            "request-1",
            "document.read",
            "report.txt",
            "POL-ALLOW",
            "ALLOW",
            None,
            {},
        ),
        (
            "EXECUTION_SUCCEEDED",
            "session-1",
            "task-1",
            "request-1",
            "document.read",
            "report.txt",
            "POL-ALLOW",
            "ALLOW",
            True,
            {},
        ),
    ]
    assert result.executed is True
    assert result.tool_result == "tool-result"
