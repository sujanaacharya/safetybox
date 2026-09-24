"""Contaminated development validation for PROC-ADAPTER@1; not held-out evidence."""

from __future__ import annotations

import hashlib
import io
import signal
import subprocess
import time
from dataclasses import FrozenInstanceError, dataclass, field
from pathlib import Path

import pytest

from safetybox import Capability, Decision, TaskContract, TaskContractPolicy
from safetybox.audit import AuditRecorder, InMemoryAuditSink
from safetybox.authorization import AuthorizationComponent, CompoundActionAuthorizer
from safetybox.events import EventType, SafetyBoxEvent
from safetybox.filesystem import LogicalHostMapper
from safetybox.models import ActionRequest
from safetybox.process import (
    PROCESS_ADAPTER_VERSION,
    PROCESS_AUDIT_ENVELOPE_VERSION,
    PROCESS_CANONICALIZATION_VERSION,
    PROCESS_ENVIRONMENT_PROFILE,
    CaptureStatus,
    ProcessAdapter,
    ProcessCanonicalizationError,
    ProcessIndeterminateError,
    ProcessObservation,
    ProcessRequest,
    ProcessResultCategory,
    ProcessSpawnError,
    ProcessTerminalClass,
    ProcessValidationStatus,
    RealProcessPrimitive,
    canonicalize_executable,
    canonicalize_process_cwd,
    commit_argv,
)
from safetybox.process.primitive import OUTPUT_RETURN_LIMIT
from safetybox.process.validation import ProcessTargetValidator

DEV_POLICY_REFERENCE = "DEV-PROC-TASK-CONTRACT@1"


@pytest.fixture(scope="session")
def native_helper(tmp_path_factory: pytest.TempPathFactory) -> Path:
    build = tmp_path_factory.mktemp("safetybox-dev-proc-helper")
    source = Path(__file__).parents[1] / "fixtures" / "process_helper.c"
    output = build / "process-helper"
    subprocess.run(
        ("/usr/bin/cc", "-std=c11", "-O2", str(source), "-o", str(output)),
        check=True,
        stdin=subprocess.DEVNULL,
        capture_output=True,
    )
    return output


@pytest.fixture
def workspace_root(tmp_path: Path) -> Path:
    root = tmp_path / "isolated-root"
    (root / "workspace" / "allowed").mkdir(parents=True)
    (root / "workspace" / "other").mkdir()
    return root


def process_request(
    executable: str,
    *,
    argv: tuple[str, ...] = ("exit", "0"),
    cwd: str = "/workspace/allowed",
    timeout_ms: int = 1000,
    task_id: str = "dev-proc-task",
    request_id: str = "DEV-PROC-REQUEST-001",
    session_id: str = "dev-proc-session",
) -> ProcessRequest:
    return ProcessRequest(
        session_id,
        task_id,
        request_id,
        "development-agent",
        executable,
        argv,
        cwd,
        timeout_ms,
    )


def adapter_for(
    root: Path,
    capabilities: list[Capability],
    *,
    primitive: RealProcessPrimitive | None = None,
    sink: object | None = None,
) -> tuple[ProcessAdapter, object, RealProcessPrimitive]:
    selected_sink = InMemoryAuditSink() if sink is None else sink
    selected_primitive = RealProcessPrimitive() if primitive is None else primitive
    contract = TaskContract("dev-proc-task", "development process task", capabilities)
    adapter = ProcessAdapter(
        mapper=LogicalHostMapper(root),
        authorizer=TaskContractPolicy(contract),
        policy_reference=DEV_POLICY_REFERENCE,
        audit_recorder=AuditRecorder(selected_sink),  # type: ignore[arg-type]
        primitive=selected_primitive,
    )
    return adapter, selected_sink, selected_primitive


def allowed_capabilities(executable: str, cwd: str = "/workspace/allowed") -> list[Capability]:
    return [Capability("process.exec", executable), Capability("process.cwd", cwd)]


def test_versions_are_explicit_and_stable() -> None:
    assert PROCESS_ADAPTER_VERSION == "PROC-ADAPTER@1"
    assert PROCESS_CANONICALIZATION_VERSION == "PROC-CANONICALIZATION@1"
    assert PROCESS_AUDIT_ENVELOPE_VERSION == "PROC-AUDIT-ENVELOPE@1"
    assert PROCESS_ENVIRONMENT_PROFILE == "PROC-ENV-MINIMAL@1"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("/controlled/bin/tool", "/controlled/bin/tool"),
        ("//controlled///bin/./tool", "/controlled/bin/tool"),
        ("/controlled/x/../bin/tool", "/controlled/bin/tool"),
        ("/../../controlled/bin/tool", "/controlled/bin/tool"),
    ],
)
def test_executable_canonicalization_is_pure_lexical(raw: str, expected: str) -> None:
    assert canonicalize_executable(raw) == expected


@pytest.mark.parametrize("raw", ["", "tool", "./tool", "../tool", "a/b", "x\x00y"])
def test_relative_bare_empty_and_nul_executables_are_rejected(raw: str) -> None:
    with pytest.raises(ProcessCanonicalizationError):
        canonicalize_executable(raw)


def test_process_cwd_requires_absolute_workspace_syntax() -> None:
    assert canonicalize_process_cwd("/workspace/a/../allowed") == "/workspace/allowed"
    with pytest.raises(ProcessCanonicalizationError):
        canonicalize_process_cwd("allowed")
    with pytest.raises(ProcessCanonicalizationError):
        canonicalize_process_cwd("/tmp/allowed")


def test_canonicalizers_reject_non_unicode_values() -> None:
    with pytest.raises(ProcessCanonicalizationError):
        canonicalize_executable(b"/bin/tool")  # type: ignore[arg-type]
    with pytest.raises(ProcessCanonicalizationError):
        canonicalize_process_cwd(b"/workspace")  # type: ignore[arg-type]


def test_argv_commitments_preserve_exact_unicode_and_order() -> None:
    values = ("", "é", "e\u0301", "with spaces")
    commitments, tuple_digest = commit_argv(values)
    assert [item.utf8_length for item in commitments] == [0, 2, 3, 11]
    assert commitments[1].sha256 != commitments[2].sha256
    assert tuple_digest == hashlib.sha256('["","é","é","with spaces"]'.encode()).hexdigest()


@pytest.mark.parametrize(
    "argv",
    [
        tuple("x" for _ in range(65)),
        ("x" * 4097,),
        tuple("x" * 4096 for _ in range(5)),
        ("bad\x00value",),
    ],
)
def test_argv_bounds_reject_before_authorization(argv: tuple[str, ...]) -> None:
    with pytest.raises(ProcessCanonicalizationError):
        commit_argv(argv)


def test_argv_and_timeout_type_boundaries_are_rejected() -> None:
    with pytest.raises(ProcessCanonicalizationError):
        commit_argv((object(),))  # type: ignore[arg-type]
    from safetybox.process.canonicalization import validate_timeout

    for timeout in (True, 49, 2001):
        with pytest.raises(ProcessCanonicalizationError):
            validate_timeout(timeout)


def test_request_is_immutable_and_copies_argv(native_helper: Path) -> None:
    supplied = ["exit", "0"]
    request = process_request(str(native_helper), argv=supplied)  # type: ignore[arg-type]
    supplied.append("changed")
    assert request.argv == ("exit", "0")
    with pytest.raises(FrozenInstanceError):
        request.task_id = "changed"  # type: ignore[misc]


def test_request_rejects_empty_identity(native_helper: Path) -> None:
    with pytest.raises(ValueError):
        ProcessRequest("", "task", "request", "actor", str(native_helper), (), "/workspace", 50)


def test_adapter_rejects_empty_policy_reference(workspace_root: Path) -> None:
    with pytest.raises(ValueError):
        ProcessAdapter(
            mapper=LogicalHostMapper(workspace_root),
            authorizer=TaskContractPolicy(TaskContract("task", "test")),
            policy_reference="",
        )


def test_adapter_rejects_a_shadow_authorizer(workspace_root: Path) -> None:
    class ShadowAuthorizer:
        pass

    with pytest.raises(TypeError, match="TaskContractPolicy"):
        ProcessAdapter(
            mapper=LogicalHostMapper(workspace_root),
            authorizer=ShadowAuthorizer(),  # type: ignore[arg-type]
            policy_reference=DEV_POLICY_REFERENCE,
        )


@pytest.mark.parametrize(
    ("executable", "cwd", "timeout"),
    [
        ("relative-tool", "/workspace/allowed", 1000),
        ("/missing/tool", "relative-cwd", 1000),
        ("/missing/tool", "/workspace/allowed", 49),
    ],
)
def test_adapter_canonicalization_failures_are_fail_closed_before_authorization(
    workspace_root: Path, executable: str, cwd: str, timeout: int
) -> None:
    adapter, _, primitive = adapter_for(workspace_root, [])
    result = adapter.execute(process_request(executable, cwd=cwd, timeout_ms=timeout))
    assert result.category is ProcessResultCategory.FAIL_CLOSED
    assert result.terminal_class is ProcessTerminalClass.FAIL_CLOSED_NOT_SPAWNED
    assert result.evidence.authorizations == ()
    assert primitive.invocation_count == 0


def test_invalid_identifier_is_governed_and_fails_closed(workspace_root: Path) -> None:
    adapter, _, primitive = adapter_for(workspace_root, [])
    request = process_request(b"/not-unicode")  # type: ignore[arg-type]
    result = adapter.execute(request)
    assert result.evidence.requested_executable.startswith("governed-sha256:")
    assert result.category is ProcessResultCategory.FAIL_CLOSED
    assert primitive.invocation_count == 0


def test_real_child_preserves_shell_looking_argv_exactly(
    native_helper: Path, workspace_root: Path
) -> None:
    literals = (
        ";",
        "&&",
        "|",
        ">",
        "$(touch nope)",
        "`touch nope`",
        "*",
        "'single' \"double\"",
        "with spaces",
        "",
        "हिमाल",
    )
    adapter, _, primitive = adapter_for(workspace_root, allowed_capabilities(str(native_helper)))
    result = adapter.execute(process_request(str(native_helper), argv=("argv", *literals)))

    assert result.succeeded
    assert result.stdout == b"\0".join(value.encode() for value in literals) + b"\0"
    assert primitive.invocation_count == 1
    assert primitive.invocations[0].executable == str(native_helper)
    assert primitive.invocations[0].argv == ("argv", *literals)
    assert primitive.invocations[0].cwd == workspace_root / "workspace" / "allowed"
    assert not (workspace_root / "workspace" / "allowed" / "nope").exists()


@pytest.mark.parametrize(
    ("exec_allowed", "cwd_allowed", "expected"),
    [
        (True, True, ProcessResultCategory.ALLOW_SUCCESS),
        (True, False, ProcessResultCategory.DENY),
        (False, True, ProcessResultCategory.DENY),
        (False, False, ProcessResultCategory.DENY),
    ],
)
def test_all_four_compound_authorization_cases_retain_both_decisions(
    native_helper: Path,
    workspace_root: Path,
    exec_allowed: bool,
    cwd_allowed: bool,
    expected: ProcessResultCategory,
) -> None:
    capabilities: list[Capability] = []
    if exec_allowed:
        capabilities.append(Capability("process.exec", str(native_helper)))
    if cwd_allowed:
        capabilities.append(Capability("process.cwd", "/workspace/allowed"))
    adapter, _, primitive = adapter_for(workspace_root, capabilities)

    result = adapter.execute(process_request(str(native_helper)))

    assert result.category is expected
    assert len(result.evidence.authorizations) == 2
    assert [item.action for item in result.evidence.authorizations] == [
        "process.exec",
        "process.cwd",
    ]
    assert [item.resource for item in result.evidence.authorizations] == [
        str(native_helper),
        "/workspace/allowed",
    ]
    assert primitive.invocation_count == (1 if exec_allowed and cwd_allowed else 0)
    if not (exec_allowed and cwd_allowed):
        assert result.evidence.executable_validation is ProcessValidationStatus.NOT_ATTEMPTED
        assert result.evidence.cwd_validation is ProcessValidationStatus.NOT_ATTEMPTED


def test_task_mismatch_denies_both_components_without_spawn(
    native_helper: Path, workspace_root: Path
) -> None:
    adapter, _, primitive = adapter_for(workspace_root, allowed_capabilities(str(native_helper)))
    result = adapter.execute(process_request(str(native_helper), task_id="wrong-task"))
    assert result.category is ProcessResultCategory.DENY
    assert [item.rule_id for item in result.evidence.authorizations] == [
        "POL-M2-TASK-MISMATCH",
        "POL-M2-TASK-MISMATCH",
    ]
    assert all(item.task_id == "wrong-task" for item in result.evidence.authorizations)
    assert primitive.invocation_count == 0


@pytest.mark.parametrize("suffix", ["2", "-old", "s/x"])
def test_exact_executable_capability_does_not_authorize_near_paths(
    native_helper: Path, workspace_root: Path, suffix: str
) -> None:
    adapter, _, primitive = adapter_for(workspace_root, allowed_capabilities(str(native_helper)))
    result = adapter.execute(process_request(f"{native_helper}{suffix}"))
    assert result.category is ProcessResultCategory.DENY
    assert result.evidence.authorizations[0].rule_id == "POL-M2-RESOURCE-OUT-OF-SCOPE"
    assert primitive.invocation_count == 0


def test_authorization_explanation_is_complete_for_denial(
    native_helper: Path, workspace_root: Path
) -> None:
    adapter, _, _ = adapter_for(workspace_root, [Capability("process.cwd", "/workspace/allowed")])
    result = adapter.execute(process_request(str(native_helper)))
    denied = result.evidence.authorizations[0]
    assert denied.component == "process.exec"
    assert denied.session_id == "dev-proc-session"
    assert denied.task_id == "dev-proc-task"
    assert denied.action == "process.exec"
    assert denied.resource == str(native_helper)
    assert denied.decision is Decision.DENY
    assert denied.rule_id == "POL-M2-CAPABILITY-MISSING"
    assert denied.reason
    assert denied.authority_source == "TaskContract"
    assert denied.contract_reference == DEV_POLICY_REFERENCE


def test_denied_request_has_no_target_probe_child_or_marker(
    native_helper: Path,
    workspace_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probes: list[str] = []

    def prohibited_probe(*args: object, **kwargs: object) -> object:
        del args, kwargs
        probes.append("called")
        raise AssertionError("target-dependent host probe occurred before complete allow")

    monkeypatch.setattr("safetybox.process.validation.os.lstat", prohibited_probe)
    monkeypatch.setattr("safetybox.process.validation.os.access", prohibited_probe)
    monkeypatch.setattr("safetybox.process.validation.os.open", prohibited_probe)
    monkeypatch.setattr(LogicalHostMapper, "to_host", prohibited_probe)
    adapter, _, primitive = adapter_for(
        workspace_root, [Capability("process.cwd", "/workspace/allowed")]
    )
    marker = workspace_root / "workspace" / "allowed" / "denied-marker.txt"

    result = adapter.execute(
        process_request(str(native_helper), argv=("marker", "denied-marker.txt"))
    )

    assert result.decision is Decision.DENY
    assert probes == []
    assert primitive.invocation_count == 0
    assert result.evidence.child_created is False
    assert result.evidence.child_token is None
    assert result.evidence.pid is None
    assert result.stdout is result.stderr is None
    assert not marker.exists()


def test_compound_authorization_evidence_is_recursively_immutable(
    native_helper: Path,
) -> None:
    request = ActionRequest(
        "request",
        "session",
        "task",
        "development-agent",
        "process.exec",
        str(native_helper),
    )
    cwd_request = ActionRequest(
        "request",
        "session",
        "task",
        "development-agent",
        "process.cwd",
        "/workspace/allowed",
    )
    policy = TaskContractPolicy(
        TaskContract("task", "test", allowed_capabilities(str(native_helper)))
    )
    decision = CompoundActionAuthorizer(
        policy,
        (AuthorizationComponent("process.cwd", cwd_request),),
        primary_name="process.exec",
    ).authorize(request)
    records = decision.metadata["subdecisions"]
    assert isinstance(records, tuple)
    first = records[0]
    with pytest.raises(TypeError):
        first["decision"] = "DENY"  # type: ignore[index]
    capability = first["applicable_capability"]  # type: ignore[index]
    with pytest.raises(TypeError):
        capability["resource"] = "/changed"  # type: ignore[index]


@pytest.mark.parametrize("kind", ["missing", "directory", "nonexec", "script", "symlink"])
def test_executable_validation_rejects_after_allow_without_spawn(
    native_helper: Path, workspace_root: Path, tmp_path: Path, kind: str
) -> None:
    target = tmp_path / f"dev-{kind}"
    if kind == "directory":
        target.mkdir()
    elif kind == "nonexec":
        target.write_bytes(b"\x7fELF")
        target.chmod(0o600)
    elif kind == "script":
        target.write_text("#!/bin/sh\nexit 0\n")
        target.chmod(0o700)
    elif kind == "symlink":
        target.symlink_to(native_helper)
    adapter, _, primitive = adapter_for(workspace_root, allowed_capabilities(str(target)))
    result = adapter.execute(process_request(str(target)))
    assert result.terminal_class is ProcessTerminalClass.VALIDATION_REJECT_NOT_SPAWNED
    assert result.decision is Decision.ALLOW
    assert result.evidence.executable_validation is ProcessValidationStatus.REJECTED
    assert primitive.invocation_count == 0


@pytest.mark.parametrize("kind", ["missing", "file", "symlink"])
def test_cwd_validation_rejects_after_both_allows(
    native_helper: Path, workspace_root: Path, kind: str
) -> None:
    logical = f"/workspace/{kind}"
    host = workspace_root / "workspace" / kind
    if kind == "file":
        host.write_text("not a directory")
    elif kind == "symlink":
        host.symlink_to(workspace_root / "workspace" / "allowed", target_is_directory=True)
    adapter, _, primitive = adapter_for(
        workspace_root, allowed_capabilities(str(native_helper), logical)
    )
    result = adapter.execute(process_request(str(native_helper), cwd=logical))
    assert result.terminal_class is ProcessTerminalClass.VALIDATION_REJECT_NOT_SPAWNED
    assert result.evidence.executable_validation is ProcessValidationStatus.SUCCEEDED
    assert result.evidence.cwd_validation is ProcessValidationStatus.REJECTED
    assert primitive.invocation_count == 0


def test_fixed_environment_does_not_inherit_parent_secret_or_path(
    native_helper: Path, workspace_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SAFETYBOX_DEV_PARENT_SECRET", "DEV-SECRET-MUST-NOT-LEAK")
    monkeypatch.setenv("PATH", "/poisoned/dev/path")
    adapter, _, primitive = adapter_for(workspace_root, allowed_capabilities(str(native_helper)))
    result = adapter.execute(process_request(str(native_helper), argv=("env",)))
    assert result.stdout is not None
    assert result.stdout.split(b"\0")[:-1] == [
        b"LANG=C.UTF-8",
        b"LC_ALL=C.UTF-8",
        b"PATH=<absent>",
        b"SAFETYBOX_DEV_PARENT_SECRET=<absent>",
    ]
    assert primitive.invocations[0].environment == (
        ("LANG", "C.UTF-8"),
        ("LC_ALL", "C.UTF-8"),
    )


def test_real_child_observes_the_mapped_host_cwd(
    native_helper: Path, workspace_root: Path
) -> None:
    adapter, _, _ = adapter_for(workspace_root, allowed_capabilities(str(native_helper)))
    result = adapter.execute(process_request(str(native_helper), argv=("cwd",)))
    expected = workspace_root / "workspace" / "allowed"
    assert result.succeeded
    assert result.stdout == str(expected).encode()
    assert result.evidence.authorizations[1].resource == "/workspace/allowed"


def test_non_utf8_child_output_remains_bytes(
    native_helper: Path, workspace_root: Path
) -> None:
    adapter, _, _ = adapter_for(workspace_root, allowed_capabilities(str(native_helper)))
    result = adapter.execute(process_request(str(native_helper), argv=("nonutf8",)))
    assert result.succeeded
    assert result.stdout == b"\xff\x00\x80"
    assert result.stderr == b"\xfe\x00\x81"


def test_real_child_can_create_local_marker_outside_filesystem_adapter(
    native_helper: Path, workspace_root: Path
) -> None:
    adapter, _, _ = adapter_for(workspace_root, allowed_capabilities(str(native_helper)))
    result = adapter.execute(process_request(str(native_helper), argv=("marker", "dev-marker.txt")))
    marker = workspace_root / "workspace" / "allowed" / "dev-marker.txt"
    assert result.succeeded
    assert marker.read_bytes() == b"created"


def test_nonzero_exit_is_tool_error_with_effect_possible(
    native_helper: Path, workspace_root: Path
) -> None:
    adapter, _, _ = adapter_for(workspace_root, allowed_capabilities(str(native_helper)))
    result = adapter.execute(
        process_request(str(native_helper), argv=("marker-fail", "partial.txt", "7"))
    )
    assert result.terminal_class is ProcessTerminalClass.PROCESS_EXIT_NONZERO_EFFECT_POSSIBLE
    assert result.category is ProcessResultCategory.TOOL_ERROR
    assert result.exit_code == 7
    assert result.evidence.effect_possible
    assert (workspace_root / "workspace" / "allowed" / "partial.txt").exists()


def test_timeout_sends_term_and_reaps_direct_child(
    native_helper: Path, workspace_root: Path
) -> None:
    adapter, _, _ = adapter_for(workspace_root, allowed_capabilities(str(native_helper)))
    result = adapter.execute(
        process_request(str(native_helper), argv=("sleep", "1000"), timeout_ms=100)
    )
    assert result.terminal_class is ProcessTerminalClass.PROCESS_TIMEOUT_EFFECT_POSSIBLE
    assert result.timed_out
    assert result.evidence.term_sent
    assert not result.evidence.kill_sent
    assert result.signal == signal.SIGTERM


def test_timeout_escalates_to_kill_when_direct_child_ignores_term(
    native_helper: Path, workspace_root: Path
) -> None:
    adapter, _, _ = adapter_for(workspace_root, allowed_capabilities(str(native_helper)))
    result = adapter.execute(
        process_request(str(native_helper), argv=("ignore-term-sleep", "1000"), timeout_ms=100)
    )
    assert result.terminal_class is ProcessTerminalClass.PROCESS_TIMEOUT_EFFECT_POSSIBLE
    assert result.evidence.term_sent
    assert result.evidence.kill_sent
    assert result.signal == signal.SIGKILL


def test_direct_child_signal_is_recorded(native_helper: Path, workspace_root: Path) -> None:
    adapter, _, _ = adapter_for(workspace_root, allowed_capabilities(str(native_helper)))
    result = adapter.execute(
        process_request(str(native_helper), argv=("signal", str(signal.SIGUSR1)))
    )
    assert result.terminal_class is ProcessTerminalClass.PROCESS_SIGNALED_EFFECT_POSSIBLE
    assert result.signal == signal.SIGUSR1
    assert not result.timed_out


def test_output_is_bounded_but_full_counts_and_hashes_are_retained(
    native_helper: Path, workspace_root: Path
) -> None:
    stdout_count = OUTPUT_RETURN_LIMIT + 100
    stderr_count = OUTPUT_RETURN_LIMIT + 50
    adapter, _, _ = adapter_for(workspace_root, allowed_capabilities(str(native_helper)))
    result = adapter.execute(
        process_request(
            str(native_helper),
            argv=("streams", str(stdout_count), str(stderr_count)),
            timeout_ms=2000,
        )
    )
    assert result.stdout == b"S" * OUTPUT_RETURN_LIMIT
    assert result.stderr == b"E" * OUTPUT_RETURN_LIMIT
    assert result.evidence.stdout.byte_count == stdout_count
    assert result.evidence.stderr.byte_count == stderr_count
    assert result.evidence.stdout.sha256 == hashlib.sha256(b"S" * stdout_count).hexdigest()
    assert result.evidence.stderr.sha256 == hashlib.sha256(b"E" * stderr_count).hexdigest()
    assert result.evidence.stdout.truncated and result.evidence.stderr.truncated
    assert result.evidence.stdout.capture_status is CaptureStatus.COMPLETE


@dataclass
class FailingEventSink:
    fail_on: EventType
    committed: list[SafetyBoxEvent] = field(default_factory=list)

    def record(self, event: SafetyBoxEvent) -> None:
        if event.event_type is self.fail_on:
            raise OSError("development injected audit failure")
        self.committed.append(event)


@pytest.mark.parametrize(
    ("event_type", "expected_decision"),
    [
        (EventType.ADAPTER_REQUEST_RECEIVED, None),
        (EventType.CANONICALIZATION_SUCCEEDED, None),
        (EventType.AUTHORIZATION_ALLOWED, Decision.ALLOW),
        (EventType.TARGET_VALIDATION_STARTED, Decision.ALLOW),
    ],
)
def test_required_pre_spawn_audit_failures_all_prevent_spawn(
    native_helper: Path,
    workspace_root: Path,
    event_type: EventType,
    expected_decision: Decision | None,
) -> None:
    sink = FailingEventSink(event_type)
    adapter, _, primitive = adapter_for(
        workspace_root, allowed_capabilities(str(native_helper)), sink=sink
    )
    result = adapter.execute(process_request(str(native_helper)))
    assert result.category is ProcessResultCategory.FAIL_CLOSED
    assert result.decision is expected_decision
    assert primitive.invocation_count == 0


def test_denial_audit_failure_preserves_historical_deny(
    native_helper: Path, workspace_root: Path
) -> None:
    sink = FailingEventSink(EventType.AUTHORIZATION_DENIED)
    adapter, _, primitive = adapter_for(workspace_root, [], sink=sink)
    result = adapter.execute(process_request(str(native_helper)))
    assert result.category is ProcessResultCategory.FAIL_CLOSED
    assert result.decision is Decision.DENY
    assert len(result.evidence.authorizations) == 2
    assert primitive.invocation_count == 0


def test_canonicalization_failure_audit_failure_still_fails_closed(
    workspace_root: Path,
) -> None:
    sink = FailingEventSink(EventType.CANONICALIZATION_FAILED)
    adapter, _, primitive = adapter_for(workspace_root, [], sink=sink)
    result = adapter.execute(process_request("relative"))
    assert result.category is ProcessResultCategory.FAIL_CLOSED
    assert primitive.invocation_count == 0


def test_required_execution_start_audit_failure_prevents_spawn(
    native_helper: Path, workspace_root: Path
) -> None:
    sink = FailingEventSink(EventType.EXECUTION_STARTED)
    adapter, _, primitive = adapter_for(
        workspace_root, allowed_capabilities(str(native_helper)), sink=sink
    )
    result = adapter.execute(process_request(str(native_helper)))
    assert result.category is ProcessResultCategory.FAIL_CLOSED
    assert result.terminal_class is ProcessTerminalClass.FAIL_CLOSED_NOT_SPAWNED
    assert primitive.invocation_count == 0


def test_terminal_audit_failure_after_spawn_is_indeterminate(
    native_helper: Path, workspace_root: Path
) -> None:
    sink = FailingEventSink(EventType.EXECUTION_SUCCEEDED)
    adapter, _, primitive = adapter_for(
        workspace_root, allowed_capabilities(str(native_helper)), sink=sink
    )
    result = adapter.execute(process_request(str(native_helper)))
    assert result.category is ProcessResultCategory.FAIL_INDETERMINATE
    assert result.terminal_class is ProcessTerminalClass.FAIL_INDETERMINATE_EXECUTION_POSSIBLE
    assert result.evidence.child_created is True
    assert primitive.invocation_count == 1


class FailingSpawnPrimitive(RealProcessPrimitive):
    def spawn_and_wait(
        self, *, executable: str, argv: tuple[str, ...], cwd: Path, timeout_ms: int
    ) -> ProcessObservation:
        self.invocations.append(self._invocation(executable, argv, cwd, timeout_ms))
        raise ProcessSpawnError(
            "PROC-SPAWN-DEV-INJECTED",
            "Development-injected spawn failure confirmed no child.",
            observation=ProcessObservation(False),
        )

    @staticmethod
    def _invocation(executable: str, argv: tuple[str, ...], cwd: Path, timeout_ms: int) -> object:
        from safetybox.process.primitive import FIXED_CHILD_ENVIRONMENT, SpawnInvocation

        return SpawnInvocation(
            executable,
            argv,
            cwd,
            tuple(sorted(FIXED_CHILD_ENVIRONMENT.items())),
            timeout_ms,
        )


def test_spawn_failure_confirmed_no_child_is_tool_error(
    native_helper: Path, workspace_root: Path
) -> None:
    primitive = FailingSpawnPrimitive()
    adapter, _, _ = adapter_for(
        workspace_root,
        allowed_capabilities(str(native_helper)),
        primitive=primitive,
    )
    result = adapter.execute(process_request(str(native_helper)))
    assert result.terminal_class is ProcessTerminalClass.SPAWN_ERROR_NOT_CREATED
    assert result.category is ProcessResultCategory.TOOL_ERROR
    assert result.evidence.child_created is False
    assert primitive.invocation_count == 1


class UnexpectedPrimitive(RealProcessPrimitive):
    def spawn_and_wait(
        self, *, executable: str, argv: tuple[str, ...], cwd: Path, timeout_ms: int
    ) -> ProcessObservation:
        raise RuntimeError("development unknown child-state failure")


def test_unexpected_primitive_failure_is_indeterminate_not_not_executed(
    native_helper: Path, workspace_root: Path
) -> None:
    adapter, _, _ = adapter_for(
        workspace_root,
        allowed_capabilities(str(native_helper)),
        primitive=UnexpectedPrimitive(),
    )
    result = adapter.execute(process_request(str(native_helper)))
    assert result.category is ProcessResultCategory.FAIL_INDETERMINATE
    assert result.evidence.primitive_invoked
    assert result.evidence.child_created is None


def test_real_primitive_treats_popen_oserror_child_state_as_indeterminate(tmp_path: Path) -> None:
    primitive = RealProcessPrimitive()
    with pytest.raises(ProcessIndeterminateError) as failure:
        primitive.spawn_and_wait(
            executable=str(tmp_path / "absent"),
            argv=(),
            cwd=tmp_path,
            timeout_ms=50,
        )
    assert failure.value.observation is not None
    assert failure.value.observation.child_created is None
    assert failure.value.observation.child_token


def test_capture_failure_after_child_creation_is_indeterminate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FailingStream:
        def read(self, size: int) -> bytes:
            del size
            raise OSError("development capture failure")

        def close(self) -> None:
            pass

    class CaptureFailingChild:
        pid = 4242
        returncode: int | None = None
        killed = False
        stdout = FailingStream()
        stderr = FailingStream()

        def wait(self, timeout: float | None = None) -> int:
            del timeout
            self.returncode = 0
            return 0

        def poll(self) -> int | None:
            return None

        def kill(self) -> None:
            self.killed = True
            self.returncode = -signal.SIGKILL

    child = CaptureFailingChild()
    monkeypatch.setattr("safetybox.process.primitive.subprocess.Popen", lambda *a, **k: child)
    primitive = RealProcessPrimitive()
    with pytest.raises(ProcessIndeterminateError) as failure:
        primitive.spawn_and_wait(
            executable="/development/native",
            argv=(),
            cwd=tmp_path,
            timeout_ms=50,
        )
    assert failure.value.observation is not None
    assert failure.value.observation.child_created is True
    assert failure.value.observation.kill_sent
    assert failure.value.observation.stdout_metadata.capture_status is CaptureStatus.FAILED


def test_capture_that_does_not_reach_eof_is_indeterminate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class BlockingStream:
        closed = False

        def read(self, size: int) -> bytes:
            del size
            while not self.closed:
                time.sleep(0.005)
            return b""

        def close(self) -> None:
            self.closed = True

    class CompletedChildWithOpenStreams:
        pid = 4343
        returncode = 0
        stdout = BlockingStream()
        stderr = BlockingStream()

        def wait(self, timeout: float | None = None) -> int:
            del timeout
            return 0

        def poll(self) -> int:
            return 0

    child = CompletedChildWithOpenStreams()
    monkeypatch.setattr("safetybox.process.primitive.subprocess.Popen", lambda *a, **k: child)
    with pytest.raises(ProcessIndeterminateError):
        RealProcessPrimitive().spawn_and_wait(
            executable="/development/native", argv=(), cwd=tmp_path, timeout_ms=50
        )
    assert child.stdout.closed and child.stderr.closed


def test_wait_and_cleanup_failure_after_child_creation_is_indeterminate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class WaitFailingChild:
        pid = 4444
        returncode: int | None = None
        stdout = io.BytesIO()
        stderr = io.BytesIO()

        def wait(self, timeout: float | None = None) -> int:
            del timeout
            raise OSError("development wait failure")

        def poll(self) -> None:
            return None

        def kill(self) -> None:
            raise OSError("development cleanup failure")

    child = WaitFailingChild()
    monkeypatch.setattr("safetybox.process.primitive.subprocess.Popen", lambda *a, **k: child)
    with pytest.raises(ProcessIndeterminateError) as failure:
        RealProcessPrimitive().spawn_and_wait(
            executable="/development/native", argv=(), cwd=tmp_path, timeout_ms=50
        )
    assert failure.value.observation is not None
    assert failure.value.observation.child_created is True


def test_validator_combined_api_returns_bound_targets(
    native_helper: Path, workspace_root: Path
) -> None:
    validator = ProcessTargetValidator(LogicalHostMapper(workspace_root))
    validated = validator.validate(str(native_helper), "/workspace/allowed")
    assert validated.executable == str(native_helper)
    assert validated.cwd == workspace_root / "workspace" / "allowed"


def test_validator_rejects_root_and_non_directory_executable_ancestor(
    workspace_root: Path, tmp_path: Path
) -> None:
    validator = ProcessTargetValidator(LogicalHostMapper(workspace_root))
    with pytest.raises(Exception, match="regular file"):
        validator.validate_executable("/")
    ancestor = tmp_path / "ancestor-file"
    ancestor.write_text("x")
    with pytest.raises(Exception, match="ancestor"):
        validator.validate_executable(str(ancestor / "tool"))


def test_validator_wraps_executable_inspection_and_read_failures(
    native_helper: Path,
    workspace_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = ProcessTargetValidator(LogicalHostMapper(workspace_root))

    def denied_lstat(path: object) -> object:
        del path
        raise PermissionError("development denied inspection")

    monkeypatch.setattr("safetybox.process.validation.os.lstat", denied_lstat)
    with pytest.raises(Exception, match="validation could not complete"):
        validator.validate_executable(str(native_helper))

    monkeypatch.undo()

    def denied_open(path: object, flags: int) -> int:
        del path, flags
        raise PermissionError("development denied read")

    monkeypatch.setattr("safetybox.process.validation.os.open", denied_open)
    with pytest.raises(Exception, match="format validation"):
        validator.validate_executable(str(native_helper))


def test_validator_wraps_cwd_inspection_failure(
    workspace_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    validator = ProcessTargetValidator(LogicalHostMapper(workspace_root))

    def denied_lstat(path: object) -> object:
        del path
        raise PermissionError("development denied cwd inspection")

    monkeypatch.setattr("safetybox.process.validation.os.lstat", denied_lstat)
    with pytest.raises(Exception, match="Cwd validation could not complete"):
        validator.validate_cwd("/workspace/allowed")


def test_authorizer_exception_preserves_both_component_attempts_and_fails_closed(
    native_helper: Path, workspace_root: Path
) -> None:
    class FailingEvaluator:
        def evaluate(self, contract: object, request: object) -> object:
            del contract, request
            raise RuntimeError("development policy unavailable")

    primitive = RealProcessPrimitive()
    policy = TaskContractPolicy(
        TaskContract("dev-proc-task", "development process task"),
        evaluator=FailingEvaluator(),  # type: ignore[arg-type]
    )
    adapter = ProcessAdapter(
        mapper=LogicalHostMapper(workspace_root),
        authorizer=policy,
        policy_reference=DEV_POLICY_REFERENCE,
        primitive=primitive,
    )
    result = adapter.execute(process_request(str(native_helper)))
    assert result.category is ProcessResultCategory.FAIL_CLOSED
    assert len(result.evidence.authorizations) == 2
    assert all(item.error_type == "RuntimeError" for item in result.evidence.authorizations)
    assert primitive.invocation_count == 0


@dataclass
class OrderingPrimitive(RealProcessPrimitive):
    sink: InMemoryAuditSink = field(default_factory=InMemoryAuditSink)
    observed_events: tuple[EventType, ...] = field(default=(), init=False)

    def spawn_and_wait(
        self, *, executable: str, argv: tuple[str, ...], cwd: Path, timeout_ms: int
    ) -> ProcessObservation:
        self.observed_events = tuple(event.event_type for event in self.sink.events())
        return super().spawn_and_wait(
            executable=executable, argv=argv, cwd=cwd, timeout_ms=timeout_ms
        )


def test_spawn_ordering_has_allow_validation_and_committed_start_first(
    native_helper: Path, workspace_root: Path
) -> None:
    sink = InMemoryAuditSink()
    primitive = OrderingPrimitive(sink)
    adapter, _, _ = adapter_for(
        workspace_root,
        allowed_capabilities(str(native_helper)),
        primitive=primitive,
        sink=sink,
    )
    result = adapter.execute(process_request(str(native_helper)))
    assert result.succeeded
    assert EventType.AUTHORIZATION_ALLOWED in primitive.observed_events
    assert primitive.observed_events.count(EventType.TARGET_VALIDATION_SUCCEEDED) == 2
    assert primitive.observed_events[-1] is EventType.EXECUTION_STARTED


def test_audit_contains_commitments_not_raw_argv_or_output(
    native_helper: Path, workspace_root: Path
) -> None:
    secret = "DEV-PROC-SENSITIVE-ARGV-3f6384"
    adapter, sink, _ = adapter_for(workspace_root, allowed_capabilities(str(native_helper)))
    result = adapter.execute(process_request(str(native_helper), argv=("argv", secret)))
    assert result.stdout == secret.encode() + b"\0"
    rendered = repr(sink.events())  # type: ignore[union-attr]
    assert secret not in rendered
    assert "argv_commitments" in rendered
    assert result.evidence.stdout.sha256 == hashlib.sha256(result.stdout).hexdigest()


def test_audit_envelope_alone_reconstructs_the_process_attempt(
    native_helper: Path, workspace_root: Path
) -> None:
    adapter, _, _ = adapter_for(workspace_root, allowed_capabilities(str(native_helper)))
    envelope = adapter.execute(process_request(str(native_helper), argv=("exit", "0"))).evidence
    assert envelope.session_id == "dev-proc-session"
    assert envelope.task_id == "dev-proc-task"
    assert envelope.request_id == envelope.correlation_id
    assert envelope.canonical_executable == str(native_helper)
    assert envelope.canonical_cwd == "/workspace/allowed"
    assert envelope.argv_count == 2
    assert len(envelope.argv_commitments) == 2
    assert len(envelope.authorizations) == 2
    assert envelope.spawn_attempted and envelope.child_created
    assert envelope.child_token and envelope.pid
    assert envelope.exit_code == 0
    assert envelope.terminal_class is ProcessTerminalClass.PROCESS_EXIT_0
    assert envelope.sequence_numbers == tuple(
        range(envelope.sequence_numbers[0], envelope.sequence_numbers[-1] + 1)
    )


def test_emitted_m3_audit_alone_reconstructs_the_process_attempt(
    native_helper: Path, workspace_root: Path
) -> None:
    adapter, sink, _ = adapter_for(workspace_root, allowed_capabilities(str(native_helper)))
    adapter.execute(process_request(str(native_helper), argv=("streams", "3", "2")))
    events = sink.events()  # type: ignore[union-attr]
    canonical = next(
        event for event in events if event.event_type is EventType.CANONICALIZATION_SUCCEEDED
    )
    authorization = next(
        event for event in events if event.event_type is EventType.AUTHORIZATION_ALLOWED
    )
    terminal = next(event for event in events if event.event_type is EventType.EXECUTION_SUCCEEDED)

    assert canonical.session_id == "dev-proc-session"
    assert canonical.task_id == "dev-proc-task"
    assert canonical.actor == "development-agent"
    assert canonical.request_id == canonical.correlation_id
    assert canonical.action == "process.exec"
    assert canonical.metadata["canonical_executable"] == str(native_helper)
    assert canonical.metadata["canonical_cwd"] == "/workspace/allowed"
    assert canonical.metadata["argv_count"] == 3
    assert len(canonical.metadata["argv_commitments"]) == 3  # type: ignore[arg-type]
    assert canonical.metadata["environment_profile"] == PROCESS_ENVIRONMENT_PROFILE
    assert canonical.metadata["timeout_ms"] == 1000
    assert len(authorization.metadata["subdecisions"]) == 2  # type: ignore[arg-type]
    assert terminal.metadata["primitive_invoked"] is True
    assert terminal.metadata["child_created"] is True
    assert terminal.metadata["child_token"]
    assert terminal.metadata["exit_code"] == 0
    assert terminal.metadata["terminal_class"] == ProcessTerminalClass.PROCESS_EXIT_0.value
    assert terminal.metadata["stdout"]["byte_count"] == 3  # type: ignore[index]
    assert terminal.metadata["stderr"]["byte_count"] == 2  # type: ignore[index]
    assert [event.sequence_number for event in events] == list(range(1, len(events) + 1))


def test_separate_requests_preserve_session_task_and_request_identity(
    native_helper: Path, workspace_root: Path
) -> None:
    adapter, _, _ = adapter_for(workspace_root, allowed_capabilities(str(native_helper)))
    first = adapter.execute(process_request(str(native_helper), request_id="DEV-PROC-IDENTITY-001"))
    second = adapter.execute(
        process_request(
            str(native_helper),
            request_id="DEV-PROC-IDENTITY-002",
            session_id="dev-proc-session-b",
        )
    )
    assert first.evidence.request_id == "DEV-PROC-IDENTITY-001"
    assert second.evidence.request_id == "DEV-PROC-IDENTITY-002"
    assert second.evidence.session_id == "dev-proc-session-b"
    assert all(item.session_id == "dev-proc-session-b" for item in second.evidence.authorizations)


def test_helper_rejects_path_bearing_marker_name(
    native_helper: Path, workspace_root: Path
) -> None:
    cwd = workspace_root / "workspace" / "allowed"
    escaped = cwd.parent / "escape.txt"
    completed = subprocess.run(
        (str(native_helper), "marker", "../escape.txt"),
        cwd=cwd,
        env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
    )
    assert completed.returncode != 0
    assert not escaped.exists()


def test_direct_popen_bypasses_adapter_as_expected_pmed_l1_boundary(
    native_helper: Path, workspace_root: Path
) -> None:
    cwd = workspace_root / "workspace" / "allowed"
    child = subprocess.Popen(
        (str(native_helper), "marker", "outside-adapter.txt"),
        cwd=cwd,
        env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
    stdout, stderr = child.communicate(timeout=2)
    assert child.returncode == 0
    assert stdout == stderr == b""
    assert (cwd / "outside-adapter.txt").read_bytes() == b"created"
