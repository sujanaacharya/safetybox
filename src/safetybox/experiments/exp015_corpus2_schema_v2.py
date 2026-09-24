"""Structure-only runtime schema and non-executing materializer for Corpus@2.

This version deliberately keeps authority questions out of schema validation.  In
particular, request and contract task IDs are independently represented; their
relationship is decided later by the frozen authorization core.
"""

from __future__ import annotations

import json
import os
import re
import stat
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path, PurePosixPath

RUNTIME_SCHEMA_ID = "EXP-015-RUNTIME-SCHEMA@2"
MATERIALIZER_ID = "EXP-015-MATERIALIZER@2"
_OPAQUE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")


class SchemaError(ValueError):
    """Raised when runtime data is structurally malformed."""


class Route(StrEnum):
    ADAPTER = "ADAPTER"
    DIRECT_CONTROL = "DIRECT_CONTROL"


class ExecutableKind(StrEnum):
    REGULAR_EXECUTABLE = "REGULAR_EXECUTABLE"
    NON_EXECUTABLE_REGULAR = "NON_EXECUTABLE_REGULAR"
    DIRECTORY = "DIRECTORY"
    SYMLINK = "SYMLINK"
    MISSING = "MISSING"
    UNSUPPORTED_SCRIPT_OR_WRAPPER = "UNSUPPORTED_SCRIPT_OR_WRAPPER"


class CwdKind(StrEnum):
    DIRECTORY = "DIRECTORY"
    MISSING = "MISSING"
    SYMLINK = "SYMLINK"
    NON_DIRECTORY = "NON_DIRECTORY"


class HelperBehavior(StrEnum):
    RECORD_ARGV = "RECORD_ARGV"
    RECORD_ENV = "RECORD_ENV"
    EMIT_STDOUT = "EMIT_STDOUT"
    EMIT_STDERR = "EMIT_STDERR"
    EMIT_BOTH = "EMIT_BOTH"
    WRITE_MARKER = "WRITE_MARKER"
    EXIT_CODE = "EXIT_CODE"
    SLEEP = "SLEEP"
    SELF_SIGNAL = "SELF_SIGNAL"
    WRITE_MARKER_THEN_EXIT = "WRITE_MARKER_THEN_EXIT"
    WRITE_MARKER_THEN_SLEEP = "WRITE_MARKER_THEN_SLEEP"


class FaultStage(StrEnum):
    PRE_EXECUTION_AUDIT = "PRE_EXECUTION_AUDIT"
    SPAWN_BEFORE_CHILD_CONFIRMED = "SPAWN_BEFORE_CHILD_CONFIRMED"
    POST_SPAWN_AUDIT = "POST_SPAWN_AUDIT"
    POST_COMPLETION_AUDIT = "POST_COMPLETION_AUDIT"
    OUTPUT_CAPTURE = "OUTPUT_CAPTURE"


class FaultMode(StrEnum):
    RAISE_CONTROLLED = "RAISE_CONTROLLED"
    RETURN_CONTROLLED_ERROR = "RETURN_CONTROLLED_ERROR"
    INTERRUPT_CAPTURE = "INTERRUPT_CAPTURE"


@dataclass(frozen=True, slots=True)
class CapabilitySpec:
    action: str
    resource: str


@dataclass(frozen=True, slots=True)
class TaskContractSpec:
    task_id: str
    capabilities: tuple[CapabilitySpec, ...]
    description: str = "EXP-015 corpus runtime contract"


@dataclass(frozen=True, slots=True)
class ProcessRequestSpec:
    session_id: str
    task_id: str
    request_id: str
    actor: str
    executable: str
    argv: tuple[str, ...]
    cwd: str
    timeout_ms: int


@dataclass(frozen=True, slots=True)
class ExecutableFixture:
    kind: ExecutableKind
    path: str
    mode: int | None = None
    content_utf8: str | None = None
    symlink_target: str | None = None
    helper: HelperBehavior | None = None
    helper_parameters: Mapping[str, str | int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CwdFixture:
    kind: CwdKind
    path: str
    mode: int | None = None
    symlink_target: str | None = None
    content_utf8: str | None = None


@dataclass(frozen=True, slots=True)
class AdditionalObject:
    path: str
    kind: str
    mode: int | None = None
    content_utf8: str | None = None
    symlink_target: str | None = None


@dataclass(frozen=True, slots=True)
class FaultInjection:
    stage: FaultStage
    mode: FaultMode
    parameters: Mapping[str, str | int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Observations:
    marker_paths: tuple[str, ...] = ()
    output_sentinels: tuple[str, ...] = ()
    environment_keys: tuple[str, ...] = ()
    channels: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RuntimeScenario:
    scenario_id: str
    request: ProcessRequestSpec
    task_contract: TaskContractSpec
    route: Route
    executable: ExecutableFixture
    cwd: CwdFixture
    additional_objects: tuple[AdditionalObject, ...] = ()
    parent_environment: Mapping[str, str] = field(default_factory=dict)
    fault_injection: FaultInjection | None = None
    observations: Observations = field(default_factory=Observations)
    schema_id: str = RUNTIME_SCHEMA_ID


@dataclass(frozen=True, slots=True)
class MaterializedScenario:
    scenario_id: str
    schema_id: str
    materializer_id: str
    request: ProcessRequestSpec
    task_contract: TaskContractSpec
    root: Path
    executable_host_path: Path
    cwd_host_path: Path
    route: Route
    fault_injection: FaultInjection | None
    observations: Observations
    parent_environment: Mapping[str, str]

    def raw_record_provenance(self) -> dict[str, str]:
        """Label-free IDs a future raw record must persist verbatim."""
        return {
            "schema_id": self.schema_id,
            "materializer_id": self.materializer_id,
            "scenario_id": self.scenario_id,
            "request_task_id": self.request.task_id,
            "contract_task_id": self.task_contract.task_id,
        }


def _opaque(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not _OPAQUE_ID.fullmatch(value):
        raise SchemaError(f"{field_name} must be a non-empty opaque ID")


def _logical_path(value: object) -> PurePosixPath:
    if not isinstance(value, str) or "\x00" in value:
        raise SchemaError("fixture path must be an absolute POSIX string")
    path = PurePosixPath(value)
    if not value.startswith("/") or ".." in path.parts or path == PurePosixPath("/"):
        raise SchemaError(f"fixture path must be a non-root absolute logical path: {value!r}")
    return path


def _host_path(root: Path, logical: str) -> Path:
    return root.joinpath(*_logical_path(logical).parts[1:])


def _enum(value: object, expected: type[StrEnum], field_name: str) -> None:
    if not isinstance(value, expected):
        raise SchemaError(f"{field_name} has invalid representation")


def _validate_fixture(executable: ExecutableFixture, cwd: CwdFixture) -> None:
    _enum(executable.kind, ExecutableKind, "executable.kind")
    _enum(cwd.kind, CwdKind, "cwd.kind")
    _logical_path(executable.path)
    _logical_path(cwd.path)
    if executable.kind is ExecutableKind.SYMLINK and not executable.symlink_target:
        raise SchemaError("SYMLINK executable requires symlink_target")
    if cwd.kind is CwdKind.SYMLINK and not cwd.symlink_target:
        raise SchemaError("SYMLINK cwd requires symlink_target")
    regular = {
        ExecutableKind.REGULAR_EXECUTABLE,
        ExecutableKind.NON_EXECUTABLE_REGULAR,
        ExecutableKind.UNSUPPORTED_SCRIPT_OR_WRAPPER,
    }
    if executable.kind in regular and executable.content_utf8 is None and executable.helper is None:
        raise SchemaError("regular executable fixture requires content_utf8 or helper")
    if executable.helper is not None:
        _enum(executable.helper, HelperBehavior, "executable.helper")
    if executable.kind is ExecutableKind.MISSING and any(
        item is not None
        for item in (executable.mode, executable.content_utf8, executable.symlink_target)
    ):
        raise SchemaError("MISSING executable cannot define object data")


def validate_runtime_scenario(scenario: RuntimeScenario) -> None:
    """Validate structure only; no authorization or outcome decision is made here."""
    if not isinstance(scenario, RuntimeScenario):
        raise SchemaError("scenario has invalid representation")
    if scenario.schema_id != RUNTIME_SCHEMA_ID:
        raise SchemaError(f"schema_id must be {RUNTIME_SCHEMA_ID}")
    _opaque(scenario.scenario_id, "scenario_id")
    request, contract = scenario.request, scenario.task_contract
    if not isinstance(request, ProcessRequestSpec) or not isinstance(contract, TaskContractSpec):
        raise SchemaError("request and task_contract are required")
    for name, value in (
        ("request.session_id", request.session_id),
        ("request.task_id", request.task_id),
        ("request.request_id", request.request_id),
        ("request.actor", request.actor),
        ("task_contract.task_id", contract.task_id),
    ):
        _opaque(value, name)
    _logical_path(request.executable)
    _logical_path(request.cwd)
    if (
        not isinstance(request.argv, tuple)
        or not request.argv
        or not all(isinstance(item, str) for item in request.argv)
    ):
        raise SchemaError("argv must be a non-empty tuple of strings")
    if (
        isinstance(request.timeout_ms, bool)
        or not isinstance(request.timeout_ms, int)
        or request.timeout_ms <= 0
    ):
        raise SchemaError("timeout_ms must be a positive integer")
    if not isinstance(contract.capabilities, tuple):
        raise SchemaError("capabilities must be a tuple")
    for capability in contract.capabilities:
        if (
            not isinstance(capability, CapabilitySpec)
            or not isinstance(capability.action, str)
            or not capability.action
            or not isinstance(capability.resource, str)
        ):
            raise SchemaError("capabilities require non-empty action and string resource")
        _logical_path(capability.resource)
    _enum(scenario.route, Route, "route")
    _validate_fixture(scenario.executable, scenario.cwd)
    for obj in scenario.additional_objects:
        if not isinstance(obj, AdditionalObject):
            raise SchemaError("additional object has invalid representation")
        _logical_path(obj.path)
        if obj.kind not in {"DIRECTORY", "REGULAR", "SYMLINK"}:
            raise SchemaError("additional object kind is invalid")
        if obj.kind == "SYMLINK" and not obj.symlink_target:
            raise SchemaError("SYMLINK additional object requires symlink_target")
    if any(
        not isinstance(key, str) or not key or "=" in key or not isinstance(value, str)
        for key, value in scenario.parent_environment.items()
    ):
        raise SchemaError("parent environment must have non-empty string names and values")
    if scenario.fault_injection is not None:
        _enum(scenario.fault_injection.stage, FaultStage, "fault stage")
        _enum(scenario.fault_injection.mode, FaultMode, "fault mode")


def _helper_program(behavior: HelperBehavior, parameters: Mapping[str, str | int]) -> str:
    payload = json.dumps(
        {"behavior": behavior.value, "parameters": dict(parameters)}, sort_keys=True
    )
    return "#!/usr/bin/env python3\nimport json, os, signal, sys, time\n" + (
        f"spec = json.loads({payload!r})\np = spec['parameters']; b = spec['behavior']\n"
        "marker = p.get('marker_path')\n"
        "if b == 'RECORD_ARGV':\n"
        "    open(str(marker), 'w', encoding='utf-8').write(json.dumps(sys.argv[1:]))\n"
        "elif b == 'RECORD_ENV':\n"
        "    captured_env = json.dumps(dict(os.environ), sort_keys=True)\n"
        "    open(str(marker), 'w', encoding='utf-8').write(captured_env)\n"
        "elif b == 'EMIT_STDOUT': print(str(p.get('text', '')))\n"
        "elif b == 'EMIT_STDERR': print(str(p.get('text', '')), file=sys.stderr)\n"
        "elif b == 'EMIT_BOTH':\n"
        "    print(str(p.get('stdout', '')))\n"
        "    print(str(p.get('stderr', '')), file=sys.stderr)\n"
        "elif b in ('WRITE_MARKER', 'WRITE_MARKER_THEN_EXIT', 'WRITE_MARKER_THEN_SLEEP'):\n"
        "    open(str(marker), 'w', encoding='utf-8').write(str(p.get('marker_text', 'marker')))\n"
        "if b in ('SLEEP', 'WRITE_MARKER_THEN_SLEEP'):\n"
        "    time.sleep(int(p.get('duration_ms', 1)) / 1000)\n"
        "if b == 'SELF_SIGNAL': os.kill(os.getpid(), int(p.get('signal', signal.SIGTERM)))\n"
        "if b in ('EXIT_CODE', 'WRITE_MARKER_THEN_EXIT'): sys.exit(int(p.get('code', 0)))\n"
    )


def _write_object(
    path: Path, kind: str, mode: int | None, content: str | None, target: str | None
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if kind == "DIRECTORY":
        path.mkdir(exist_ok=True)
    elif kind == "SYMLINK":
        assert target is not None
        path.symlink_to(target)
    else:
        path.write_text(content or "", encoding="utf-8")
    if mode is not None and not path.is_symlink():
        path.chmod(mode)


def materialize(scenario: RuntimeScenario, temp_root: Path) -> MaterializedScenario:
    """Create declared fixture state, without execution or authorization evaluation."""
    validate_runtime_scenario(scenario)
    temp_root.mkdir(parents=True, exist_ok=True)
    for obj in scenario.additional_objects:
        _write_object(
            _host_path(temp_root, obj.path),
            obj.kind,
            obj.mode,
            obj.content_utf8,
            obj.symlink_target,
        )
    exe, cwd = scenario.executable, scenario.cwd
    exe_host, cwd_host = _host_path(temp_root, exe.path), _host_path(temp_root, cwd.path)
    if exe.kind is not ExecutableKind.MISSING:
        kind = (
            "SYMLINK"
            if exe.kind is ExecutableKind.SYMLINK
            else "DIRECTORY"
            if exe.kind is ExecutableKind.DIRECTORY
            else "REGULAR"
        )
        content = (
            _helper_program(exe.helper, exe.helper_parameters) if exe.helper else exe.content_utf8
        )
        default_mode = 0o755 if exe.kind is ExecutableKind.REGULAR_EXECUTABLE else 0o644
        _write_object(
            exe_host,
            kind,
            exe.mode if exe.mode is not None else default_mode,
            content,
            exe.symlink_target,
        )
    if cwd.kind is not CwdKind.MISSING:
        kind = (
            "SYMLINK"
            if cwd.kind is CwdKind.SYMLINK
            else "DIRECTORY"
            if cwd.kind is CwdKind.DIRECTORY
            else "REGULAR"
        )
        _write_object(
            cwd_host,
            kind,
            cwd.mode if cwd.mode is not None else 0o755,
            cwd.content_utf8,
            cwd.symlink_target,
        )
    return MaterializedScenario(
        scenario.scenario_id,
        RUNTIME_SCHEMA_ID,
        MATERIALIZER_ID,
        scenario.request,
        scenario.task_contract,
        temp_root,
        exe_host,
        cwd_host,
        scenario.route,
        scenario.fault_injection,
        scenario.observations,
        dict(scenario.parent_environment),
    )


def normalized_state(materialized: MaterializedScenario) -> dict[str, object]:
    """Describe fixture state while intentionally omitting scenario and task identities."""

    def describe(path: Path) -> dict[str, object]:
        relative = path.relative_to(materialized.root).as_posix()
        if not os.path.lexists(path):
            return {"path": relative, "type": "MISSING"}
        data: dict[str, object] = {"path": relative, "mode": stat.S_IMODE(path.lstat().st_mode)}
        if path.is_symlink():
            data.update(type="SYMLINK", target=os.readlink(path))
        elif path.is_dir():
            data["type"] = "DIRECTORY"
        else:
            data.update(type="REGULAR", content=path.read_text(encoding="utf-8"))
        return data

    return {
        "executable": describe(materialized.executable_host_path),
        "cwd": describe(materialized.cwd_host_path),
        "route": materialized.route.value,
        "fault": None
        if materialized.fault_injection is None
        else {
            "stage": materialized.fault_injection.stage.value,
            "mode": materialized.fault_injection.mode.value,
            "parameters": dict(materialized.fault_injection.parameters),
        },
        "parent_environment_keys": sorted(materialized.parent_environment),
        "observation_channels": list(materialized.observations.channels),
    }
