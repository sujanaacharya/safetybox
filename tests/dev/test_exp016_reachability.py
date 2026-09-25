"""Contaminated development-only proofs for frozen EXP-016 infrastructure."""

from __future__ import annotations

import hashlib
import os
import signal
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pytest

from safetybox import Capability, Decision, TaskContract, TaskContractPolicy
from safetybox.audit import AuditRecorder, InMemoryAuditSink
from safetybox.events import EventType, SafetyBoxEvent
from safetybox.experiments.exp016_reachability import (
    CwdState,
    ExecutableState,
    Route,
    decode_environment,
    decode_frames,
    expected_pattern,
    require_cwd_state,
    require_executable_state,
    run_native_direct,
    smoke_test_helper,
)
from safetybox.filesystem import LogicalHostMapper
from safetybox.process import (
    CaptureStatus,
    ProcessAdapter,
    ProcessIndeterminateError,
    ProcessObservation,
    ProcessRequest,
    ProcessResultCategory,
    ProcessSpawnError,
    ProcessTerminalClass,
    ProcessValidationStatus,
    RealProcessPrimitive,
)
from safetybox.process.primitive import (
    FIXED_CHILD_ENVIRONMENT,
    OUTPUT_RETURN_LIMIT,
    SpawnInvocation,
)

ROOT = Path(__file__).parents[2]
HELPER = ROOT / "experiments" / "EXP-016" / "fixture" / "native-helper"
POLICY_REFERENCE = "EXP-016-DEVELOPMENT-TASK-CONTRACT@1"
MARKER_PAYLOAD = b"EXP016\x00\xa6"


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    (root / "workspace" / "allowed").mkdir(parents=True)
    (root / "workspace" / "alternate").mkdir()
    return root


def request(
    argv: tuple[str, ...],
    *,
    cwd: str = "/workspace/allowed",
    timeout_ms: int = 1000,
    task_id: str = "exp016-development-task",
    request_id: str = "DEV016-REQUEST",
) -> ProcessRequest:
    return ProcessRequest(
        "exp016-development-session",
        task_id,
        request_id,
        "exp016-development-actor",
        str(HELPER),
        argv,
        cwd,
        timeout_ms,
    )


def adapter_for(
    workspace: Path,
    *,
    allow: bool = True,
    cwd: str = "/workspace/allowed",
    sink: object | None = None,
    primitive: RealProcessPrimitive | None = None,
) -> tuple[ProcessAdapter, object, RealProcessPrimitive]:
    capabilities = (
        [Capability("process.exec", str(HELPER)), Capability("process.cwd", cwd)] if allow else []
    )
    selected_sink = InMemoryAuditSink() if sink is None else sink
    selected_primitive = RealProcessPrimitive() if primitive is None else primitive
    contract = TaskContract("exp016-development-task", "EXP-016 contaminated proof", capabilities)
    return (
        ProcessAdapter(
            mapper=LogicalHostMapper(workspace),
            authorizer=TaskContractPolicy(contract),
            policy_reference=POLICY_REFERENCE,
            audit_recorder=AuditRecorder(selected_sink),  # type: ignore[arg-type]
            primitive=selected_primitive,
        ),
        selected_sink,
        selected_primitive,
    )


def test_direct_helper_smoke_covers_every_frozen_mode(tmp_path: Path) -> None:
    observed = require_executable_state(HELPER, ExecutableState.VALID_NATIVE_EXECUTABLE)
    assert observed.elf is not None and observed.elf.architecture_compatible
    assert smoke_test_helper(HELPER, tmp_path) == (
        "argv",
        "env",
        "cwd",
        "stdout",
        "stderr",
        "both",
        "exit",
        "sleep",
        "signal",
        "marker",
        "marker-then-sleep",
        "marker-then-exit",
    )


def test_independent_executable_oracle_distinguishes_all_frozen_states(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing"
    directory = tmp_path / "directory"
    directory.mkdir()
    nonexec = tmp_path / "nonexec"
    nonexec.write_bytes(b"\x7fELF")
    nonexec.chmod(0o600)
    script = tmp_path / "script"
    script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    script.chmod(0o700)
    symlink = tmp_path / "symlink"
    symlink.symlink_to(HELPER)
    for path, state in (
        (missing, ExecutableState.MISSING),
        (directory, ExecutableState.DIRECTORY),
        (nonexec, ExecutableState.NON_EXECUTABLE),
        (script, ExecutableState.WRAPPER_OR_SCRIPT),
        (symlink, ExecutableState.SYMLINK),
    ):
        assert require_executable_state(path, state).state is state


def test_independent_cwd_oracle_distinguishes_all_frozen_states(tmp_path: Path) -> None:
    valid = tmp_path / "valid"
    valid.mkdir()
    missing = tmp_path / "missing"
    file_path = tmp_path / "file"
    file_path.write_text("not a directory", encoding="utf-8")
    symlink = tmp_path / "link"
    symlink.symlink_to(valid, target_is_directory=True)
    for path, state in (
        (valid, CwdState.VALID_DIRECTORY),
        (missing, CwdState.MISSING),
        (file_path, CwdState.NON_DIRECTORY),
        (symlink, CwdState.SYMLINK),
    ):
        assert require_cwd_state(path, state).state is state


def test_real_adapter_child_preserves_argv_and_no_shell_literals(workspace: Path) -> None:
    literals = (
        "; rm -rf /",
        "$(whoami)",
        "`id`",
        "&&",
        "||",
        "|",
        ">",
        "<",
        "",
        "हिमाल",
    )
    adapter, _, primitive = adapter_for(workspace)
    result = adapter.execute(request(("argv", *literals)))
    assert result.succeeded
    assert result.stdout is not None
    assert decode_frames(result.stdout, b"E16A") == tuple(value.encode() for value in literals)
    assert primitive.invocation_count == 1
    assert primitive.invocations[0].argv == ("argv", *literals)
    assert not any((workspace / "workspace" / "allowed").iterdir())


def test_real_adapter_child_observes_only_frozen_environment(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", "/development/secret-home")
    monkeypatch.setenv("PATH", "/development/poisoned-path")
    monkeypatch.setenv("EXP016_PARENT_SECRET", "must-not-cross")
    adapter, _, primitive = adapter_for(workspace)
    result = adapter.execute(request(("env",)))
    assert result.succeeded and result.stdout is not None
    assert decode_environment(result.stdout) == {
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": None,
        "HOME": None,
        "EXP016_PARENT_SECRET": None,
    }
    assert primitive.invocations[0].environment == tuple(sorted(FIXED_CHILD_ENVIRONMENT.items()))


def test_real_adapter_child_observes_physical_cwd_and_marker(workspace: Path) -> None:
    adapter, _, _ = adapter_for(workspace, cwd="/workspace/alternate")
    cwd_result = adapter.execute(request(("cwd",), cwd="/workspace/alternate"))
    assert cwd_result.succeeded and cwd_result.stdout is not None
    length = int.from_bytes(cwd_result.stdout[4:8], "big")
    assert cwd_result.stdout[:4] == b"E16C"
    assert cwd_result.stdout[8 : 8 + length] == str(workspace / "workspace" / "alternate").encode()

    marker_result = adapter.execute(
        request(("marker", "development-marker.bin"), cwd="/workspace/alternate")
    )
    assert marker_result.succeeded
    assert (
        workspace / "workspace" / "alternate" / "development-marker.bin"
    ).read_bytes() == MARKER_PAYLOAD


@pytest.mark.parametrize(
    "count",
    [0, OUTPUT_RETURN_LIMIT - 1, OUTPUT_RETURN_LIMIT, OUTPUT_RETURN_LIMIT + 1, 70000],
)
def test_real_adapter_output_metadata_is_truthful(workspace: Path, count: int) -> None:
    adapter, _, _ = adapter_for(workspace)
    result = adapter.execute(request(("both", str(count), str(count)), timeout_ms=2000))
    expected_stdout = expected_pattern(b"O16:", count)
    expected_stderr = expected_pattern(b"E16:", count)
    assert result.succeeded
    assert result.stdout == expected_stdout[:OUTPUT_RETURN_LIMIT]
    assert result.stderr == expected_stderr[:OUTPUT_RETURN_LIMIT]
    assert result.evidence.stdout.byte_count == count
    assert result.evidence.stderr.byte_count == count
    assert result.evidence.stdout.sha256 == hashlib.sha256(expected_stdout).hexdigest()
    assert result.evidence.stderr.sha256 == hashlib.sha256(expected_stderr).hexdigest()
    assert result.evidence.stdout.truncated is (count > OUTPUT_RETURN_LIMIT)
    assert result.evidence.stderr.truncated is (count > OUTPUT_RETURN_LIMIT)
    assert result.evidence.stdout.capture_status is CaptureStatus.COMPLETE


@pytest.mark.parametrize("code", [1, 7, 23])
def test_real_adapter_reports_nonzero_exit(workspace: Path, code: int) -> None:
    adapter, _, _ = adapter_for(workspace)
    result = adapter.execute(request(("exit", str(code))))
    assert result.terminal_class is ProcessTerminalClass.PROCESS_EXIT_NONZERO_EFFECT_POSSIBLE
    assert result.exit_code == code
    assert result.evidence.child_created is True


def test_real_adapter_reports_self_signal(workspace: Path) -> None:
    adapter, _, _ = adapter_for(workspace)
    result = adapter.execute(request(("signal", str(signal.SIGUSR1))))
    assert result.terminal_class is ProcessTerminalClass.PROCESS_SIGNALED_EFFECT_POSSIBLE
    assert result.signal == signal.SIGUSR1
    assert not result.timed_out


def test_real_adapter_timeout_term_and_kill_are_truthful(workspace: Path) -> None:
    adapter, _, _ = adapter_for(workspace)
    term = adapter.execute(request(("sleep", "1000"), timeout_ms=100, request_id="DEV016-TERM"))
    assert term.terminal_class is ProcessTerminalClass.PROCESS_TIMEOUT_EFFECT_POSSIBLE
    assert term.timed_out and term.evidence.term_sent and not term.evidence.kill_sent
    assert term.signal == signal.SIGTERM
    kill = adapter.execute(
        request(
            ("ignore-term-sleep", "1000"),
            timeout_ms=100,
            request_id="DEV016-KILL",
        )
    )
    assert kill.terminal_class is ProcessTerminalClass.PROCESS_TIMEOUT_EFFECT_POSSIBLE
    assert kill.timed_out and kill.evidence.term_sent and kill.evidence.kill_sent
    assert kill.signal == signal.SIGKILL


def test_cwd_validation_is_structurally_reachable_after_valid_elf(workspace: Path) -> None:
    logical = "/workspace/missing"
    adapter, _, primitive = adapter_for(workspace, cwd=logical)
    result = adapter.execute(request(("exit", "0"), cwd=logical))
    assert result.decision is Decision.ALLOW
    assert result.evidence.executable_validation is ProcessValidationStatus.SUCCEEDED
    assert result.evidence.cwd_validation is ProcessValidationStatus.REJECTED
    assert result.terminal_class is ProcessTerminalClass.VALIDATION_REJECT_NOT_SPAWNED
    assert primitive.invocation_count == 0


def test_denied_control_never_reaches_validation_or_spawn(workspace: Path) -> None:
    adapter, _, primitive = adapter_for(workspace, allow=False)
    result = adapter.execute(request(("marker", "must-not-exist.bin")))
    assert result.category is ProcessResultCategory.DENY
    assert result.terminal_class is ProcessTerminalClass.POLICY_DENY_NOT_SPAWNED
    assert result.evidence.executable_validation is ProcessValidationStatus.NOT_ATTEMPTED
    assert primitive.invocation_count == 0
    assert not (workspace / "workspace" / "allowed" / "must-not-exist.bin").exists()


@dataclass
class FailingSink:
    fail_on: EventType
    committed: list[SafetyBoxEvent] = field(default_factory=list)

    def record(self, event: SafetyBoxEvent) -> None:
        if event.event_type is self.fail_on:
            raise OSError("EXP-016 development-only injected audit failure")
        self.committed.append(event)


class ConfirmedNoChildPrimitive(RealProcessPrimitive):
    def spawn_and_wait(
        self, *, executable: str, argv: tuple[str, ...], cwd: Path, timeout_ms: int
    ) -> ProcessObservation:
        self.invocations.append(
            SpawnInvocation(
                executable,
                argv,
                cwd,
                tuple(sorted(FIXED_CHILD_ENVIRONMENT.items())),
                timeout_ms,
            )
        )
        raise ProcessSpawnError(
            "PROC-SPAWN-EXP016-DEVELOPMENT",
            "EXP-016 development-only confirmed no-child injection.",
            observation=ProcessObservation(False),
        )


class CaptureFailureAfterRealChildPrimitive(RealProcessPrimitive):
    def spawn_and_wait(
        self, *, executable: str, argv: tuple[str, ...], cwd: Path, timeout_ms: int
    ) -> ProcessObservation:
        observation = super().spawn_and_wait(
            executable=executable, argv=argv, cwd=cwd, timeout_ms=timeout_ms
        )
        raise ProcessIndeterminateError(
            "PROC-CAPTURE-EXP016-DEVELOPMENT",
            "EXP-016 development-only post-child capture injection.",
            observation=observation,
        )


def test_every_supported_failure_seam_has_reached_preconditions(workspace: Path) -> None:
    preaudit_sink = FailingSink(EventType.EXECUTION_STARTED)
    preaudit_adapter, _, preaudit_primitive = adapter_for(workspace, sink=preaudit_sink)
    preaudit = preaudit_adapter.execute(request(("exit", "0"), request_id="DEV016-PREAUDIT"))
    assert preaudit.terminal_class is ProcessTerminalClass.FAIL_CLOSED_NOT_SPAWNED
    assert preaudit.evidence.executable_validation is ProcessValidationStatus.SUCCEEDED
    assert preaudit.evidence.cwd_validation is ProcessValidationStatus.SUCCEEDED
    assert preaudit_primitive.invocation_count == 0

    spawn_primitive = ConfirmedNoChildPrimitive()
    spawn_adapter, spawn_sink, _ = adapter_for(workspace, primitive=spawn_primitive)
    spawn = spawn_adapter.execute(request(("exit", "0"), request_id="DEV016-SPAWN"))
    assert spawn.terminal_class is ProcessTerminalClass.SPAWN_ERROR_NOT_CREATED
    assert spawn_primitive.invocation_count == 1
    assert EventType.EXECUTION_STARTED in tuple(
        event.event_type
        for event in spawn_sink.events()  # type: ignore[union-attr]
    )

    capture_primitive = CaptureFailureAfterRealChildPrimitive()
    capture_adapter, _, _ = adapter_for(workspace, primitive=capture_primitive)
    capture = capture_adapter.execute(request(("exit", "0"), request_id="DEV016-CAPTURE"))
    assert capture.terminal_class is ProcessTerminalClass.FAIL_INDETERMINATE_EXECUTION_POSSIBLE
    assert capture.evidence.child_created is True
    assert capture.evidence.exit_code == 0

    success_sink = FailingSink(EventType.EXECUTION_SUCCEEDED)
    success_adapter, _, success_primitive = adapter_for(workspace, sink=success_sink)
    success_audit = success_adapter.execute(
        request(("exit", "0"), request_id="DEV016-TERMINAL-SUCCESS")
    )
    assert (
        success_audit.terminal_class is ProcessTerminalClass.FAIL_INDETERMINATE_EXECUTION_POSSIBLE
    )
    assert success_audit.evidence.child_created is True
    assert success_primitive.invocation_count == 1

    failure_sink = FailingSink(EventType.EXECUTION_FAILED)
    failure_adapter, _, failure_primitive = adapter_for(workspace, sink=failure_sink)
    failure_audit = failure_adapter.execute(
        request(("exit", "7"), request_id="DEV016-TERMINAL-FAILURE")
    )
    assert (
        failure_audit.terminal_class is ProcessTerminalClass.FAIL_INDETERMINATE_EXECUTION_POSSIBLE
    )
    assert failure_audit.evidence.child_created is True
    assert failure_primitive.invocation_count == 1


@dataclass
class OrderingPrimitive(RealProcessPrimitive):
    sink: InMemoryAuditSink = field(default_factory=InMemoryAuditSink)
    events_before_spawn: tuple[EventType, ...] = field(default=(), init=False)
    observed_pid: int | None = field(default=None, init=False)
    spawn_boundary_time: datetime | None = field(default=None, init=False)
    child_observed_time: datetime | None = field(default=None, init=False)

    def spawn_and_wait(
        self, *, executable: str, argv: tuple[str, ...], cwd: Path, timeout_ms: int
    ) -> ProcessObservation:
        self.events_before_spawn = tuple(event.event_type for event in self.sink.events())
        self.spawn_boundary_time = datetime.now(UTC)
        observation = super().spawn_and_wait(
            executable=executable, argv=argv, cwd=cwd, timeout_ms=timeout_ms
        )
        self.child_observed_time = datetime.now(UTC)
        self.observed_pid = observation.pid
        return observation


def test_audit_order_and_truth_match_independent_primitive_observation(workspace: Path) -> None:
    sink = InMemoryAuditSink()
    primitive = OrderingPrimitive(sink)
    adapter, _, _ = adapter_for(workspace, sink=sink, primitive=primitive)
    result = adapter.execute(request(("both", "31", "29"), request_id="DEV016-ORDER"))
    events = sink.events()
    event_types = tuple(event.event_type for event in events)
    assert result.succeeded
    assert primitive.events_before_spawn[-1] is EventType.EXECUTION_STARTED
    assert EventType.AUTHORIZATION_ALLOWED in primitive.events_before_spawn
    assert primitive.events_before_spawn.count(EventType.TARGET_VALIDATION_SUCCEEDED) == 2
    assert event_types[-1] is EventType.EXECUTION_SUCCEEDED
    execution_start = next(
        event for event in events if event.event_type is EventType.EXECUTION_STARTED
    )
    terminal = events[-1]
    assert primitive.spawn_boundary_time is not None
    assert primitive.child_observed_time is not None
    assert execution_start.timestamp <= primitive.spawn_boundary_time
    assert primitive.spawn_boundary_time <= primitive.child_observed_time <= terminal.timestamp
    assert result.evidence.pid == primitive.observed_pid
    assert result.evidence.stdout.byte_count == 31
    assert result.evidence.stderr.byte_count == 29
    assert (
        result.evidence.stdout.sha256 == hashlib.sha256(expected_pattern(b"O16:", 31)).hexdigest()
    )
    assert (
        result.evidence.stderr.sha256 == hashlib.sha256(expected_pattern(b"E16:", 29)).hexdigest()
    )
    assert result.evidence.sequence_numbers == tuple(range(1, len(events) + 1))


def test_direct_control_route_is_explicit_and_bypasses_adapter(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    route = Route.DIRECT_CONTROL
    monkeypatch.setattr(
        ProcessAdapter,
        "execute",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("adapter route used")),
    )
    cwd = workspace / "workspace" / "allowed"
    completed = run_native_direct(HELPER, ("marker", "direct-control.bin"), cwd=cwd)
    assert route is Route.DIRECT_CONTROL
    assert completed.returncode == 0
    assert (cwd / "direct-control.bin").read_bytes() == MARKER_PAYLOAD
    assert os.path.samefile(cwd, workspace / "workspace" / "allowed")
