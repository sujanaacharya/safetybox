# ruff: noqa: E501
"""EXP-015-RUN-001 label-isolated one-shot execution phase.

This process opens only runtime scenarios. It never opens labels.json or pairs.json and
never imports the Corpus@2 scoring module. Every attempt is appended and fsynced once.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, fields, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any

from safetybox import Capability, TaskContract, TaskContractPolicy
from safetybox.audit import AuditRecorder
from safetybox.events import EventType, SafetyBoxEvent
from safetybox.experiments.exp015_corpus2_schema_v2 import (
    AdditionalObject,
    CapabilitySpec,
    CwdFixture,
    CwdKind,
    ExecutableFixture,
    ExecutableKind,
    FaultInjection,
    FaultMode,
    FaultStage,
    HelperBehavior,
    MaterializedScenario,
    Observations,
    ProcessRequestSpec,
    Route,
    RuntimeScenario,
    TaskContractSpec,
    materialize,
)
from safetybox.filesystem import LogicalHostMapper
from safetybox.process import ProcessAdapter, ProcessRequest, RealProcessPrimitive
from safetybox.process.errors import ProcessIndeterminateError, ProcessSpawnError
from safetybox.process.models import CaptureStatus, ProcessResult, StreamMetadata
from safetybox.process.primitive import (
    FIXED_CHILD_ENVIRONMENT,
    ProcessObservation,
    SpawnInvocation,
)

ROOT = Path(__file__).resolve().parents[2]
RESULT = Path(__file__).resolve().parent
RUNS = RESULT / "runs.jsonl"
REPEATS = RESULT / "repeats.jsonl"
STATE = RESULT / "execution_state.json"
SCENARIOS = ROOT / "experiments/EXP-015/corpus2/scenarios.json"
REPEAT_IDS = ("C2-001", "C2-061", "C2-041", "C2-049", "C2-097", "C2-055")
PROHIBITED_MODULE_PREFIXES = ("safetybox.experiments.exp015_corpus2_scoring",)
RUNNER_VERSION = "EXP-015-RUNNER-1"


def now() -> str:
    return datetime.now(UTC).astimezone().isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def jsonable(value: object) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, bytes):
        return {
            "base64": base64.b64encode(value).decode("ascii"),
            "byte_count": len(value),
            "sha256": sha256_bytes(value),
        }
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: jsonable(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, (MappingProxyType, dict)):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(jsonable(item) for item in value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def durable_json(path: Path, value: object) -> None:
    encoded = (json.dumps(jsonable(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def append_jsonl(path: Path, value: object) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(jsonable(value), ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def assert_label_isolation() -> None:
    bad = sorted(
        name for name in sys.modules if any(name.startswith(prefix) for prefix in PROHIBITED_MODULE_PREFIXES)
    )
    if bad:
        raise RuntimeError(f"label/scoring module loaded during execution: {bad}")


def decode(raw: dict[str, object]) -> RuntimeScenario:
    request = raw["request"]
    contract = raw["task_contract"]
    executable = raw["executable"]
    cwd = raw["cwd"]
    assert isinstance(request, dict) and isinstance(contract, dict)
    assert isinstance(executable, dict) and isinstance(cwd, dict)
    fault_raw = raw["fault_injection"]
    observations = raw["observations"]
    assert isinstance(observations, dict)
    fault = None
    if isinstance(fault_raw, dict):
        fault = FaultInjection(
            FaultStage(fault_raw["stage"]), FaultMode(fault_raw["mode"]), fault_raw["parameters"]
        )
    return RuntimeScenario(
        str(raw["scenario_id"]),
        ProcessRequestSpec(
            str(request["session_id"]), str(request["task_id"]), str(request["request_id"]),
            str(request["actor"]), str(request["executable"]), tuple(request["argv"]),
            str(request["cwd"]), int(request["timeout_ms"]),
        ),
        TaskContractSpec(
            str(contract["task_id"]),
            tuple(CapabilitySpec(str(item["action"]), str(item["resource"])) for item in contract["capabilities"]),
            str(contract["description"]),
        ),
        Route(raw["route"]),
        ExecutableFixture(
            ExecutableKind(executable["kind"]), str(executable["path"]), executable.get("mode"),
            executable.get("content_utf8"), executable.get("symlink_target"),
            None if executable.get("helper") is None else HelperBehavior(executable["helper"]),
            executable.get("helper_parameters", {}),
        ),
        CwdFixture(
            CwdKind(cwd["kind"]), str(cwd["path"]), cwd.get("mode"),
            cwd.get("symlink_target"), cwd.get("content_utf8"),
        ),
        tuple(
            AdditionalObject(
                str(item["path"]), str(item["kind"]), item.get("mode"),
                item.get("content_utf8"), item.get("symlink_target"),
            )
            for item in raw["additional_objects"]
        ),
        raw["parent_environment"],
        fault,
        Observations(
            tuple(observations["marker_paths"]), tuple(observations["output_sentinels"]),
            tuple(observations["environment_keys"]), tuple(observations["channels"]),
        ),
        str(raw["schema_id"]),
    )


def runtime_scenarios() -> list[RuntimeScenario]:
    document = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    values = [decode(item) for item in document["scenarios"]]
    if len(values) != 120 or len({item.scenario_id for item in values}) != 120:
        raise RuntimeError("runtime corpus is not 120 unique scenarios")
    return values


def corpus_host_path(materialized_root: Path, logical: str) -> Path:
    return materialized_root.joinpath(*Path(logical).parts[1:])


def adapter_cwd(logical: str) -> str:
    return "/workspace" + logical


def adapter_capability(materialized_root: Path, item: CapabilitySpec) -> Capability:
    if item.action == "process.exec":
        resource = str(corpus_host_path(materialized_root, item.resource))
    elif item.action == "process.cwd":
        resource = adapter_cwd(item.resource)
    else:
        resource = item.resource
    return Capability(item.action, resource)


@contextmanager
def parent_environment(values: dict[str, str] | object) -> Iterator[None]:
    assert isinstance(values, dict)
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, old in previous.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old


@dataclass
class EvidenceSink:
    fault: FaultInjection | None = None
    primitive: RealProcessPrimitive | None = None

    def __post_init__(self) -> None:
        self.events_recorded: list[SafetyBoxEvent] = []
        self.failure_observed = False

    def record(self, event: SafetyBoxEvent) -> None:
        fail = False
        if self.fault is not None and self.fault.stage is FaultStage.PRE_EXECUTION_AUDIT:
            fail = event.event_type is EventType.EXECUTION_STARTED
        if (
            self.fault is not None
            and self.fault.stage in {FaultStage.POST_SPAWN_AUDIT, FaultStage.POST_COMPLETION_AUDIT}
            and self.primitive is not None
            and self.primitive.invocation_count > 0
            and event.event_type in {EventType.EXECUTION_SUCCEEDED, EventType.EXECUTION_FAILED}
        ):
            fail = True
        if fail:
            self.failure_observed = True
            raise OSError("EXP-015 frozen runtime-injected audit failure")
        self.events_recorded.append(event)

    def events(self) -> tuple[SafetyBoxEvent, ...]:
        return tuple(self.events_recorded)


@dataclass
class ObservingPrimitive(RealProcessPrimitive):
    sink: EvidenceSink | None = None

    def __post_init__(self) -> None:
        self.events_before_invocation: tuple[str, ...] = ()

    def spawn_and_wait(
        self, *, executable: str, argv: tuple[str, ...], cwd: Path, timeout_ms: int
    ) -> ProcessObservation:
        if self.sink is not None:
            self.events_before_invocation = tuple(event.event_type.value for event in self.sink.events())
        return super().spawn_and_wait(executable=executable, argv=argv, cwd=cwd, timeout_ms=timeout_ms)


@dataclass
class SpawnErrorPrimitive(ObservingPrimitive):
    def spawn_and_wait(
        self, *, executable: str, argv: tuple[str, ...], cwd: Path, timeout_ms: int
    ) -> ProcessObservation:
        if self.sink is not None:
            self.events_before_invocation = tuple(event.event_type.value for event in self.sink.events())
        self.invocations.append(
            SpawnInvocation(executable, argv, cwd, tuple(sorted(FIXED_CHILD_ENVIRONMENT.items())), timeout_ms)
        )
        raise ProcessSpawnError(
            "PROC-SPAWN-CORPUS-INJECTED", "The registered spawn seam reported no child.",
            observation=ProcessObservation(False),
        )


@dataclass
class CaptureErrorPrimitive(ObservingPrimitive):
    def spawn_and_wait(
        self, *, executable: str, argv: tuple[str, ...], cwd: Path, timeout_ms: int
    ) -> ProcessObservation:
        observed = super().spawn_and_wait(
            executable=executable, argv=argv, cwd=cwd, timeout_ms=timeout_ms
        )
        failed = ProcessObservation(
            observed.child_created, observed.child_token, observed.pid, observed.returncode,
            observed.timed_out, observed.term_sent, observed.kill_sent,
            stdout_metadata=StreamMetadata(None, None, False, CaptureStatus.FAILED),
            stderr_metadata=StreamMetadata(None, None, False, CaptureStatus.FAILED),
        )
        raise ProcessIndeterminateError(
            "PROC-CAPTURE-CORPUS-INJECTED", "The registered output capture seam was interrupted.",
            observation=failed,
        )


def primitive_for(fault: FaultInjection | None) -> ObservingPrimitive:
    if fault is not None and fault.stage is FaultStage.SPAWN_BEFORE_CHILD_CONFIRMED:
        return SpawnErrorPrimitive()
    if fault is not None and fault.stage is FaultStage.OUTPUT_CAPTURE:
        return CaptureErrorPrimitive()
    return ObservingPrimitive()


def stream_record(metadata: StreamMetadata, payload: bytes | None) -> dict[str, object]:
    return {
        "byte_count": metadata.byte_count,
        "sha256": metadata.sha256,
        "truncated": metadata.truncated,
        "capture_status": metadata.capture_status.value,
        "retained": jsonable(payload),
    }


def marker_observations(item: MaterializedScenario) -> list[dict[str, object]]:
    values = []
    for logical in item.observations.marker_paths:
        path = corpus_host_path(item.root, logical)
        if path.is_file() and not path.is_symlink():
            data = path.read_bytes()
            values.append({"path": logical, "present": True, "byte_count": len(data), "sha256": sha256_bytes(data), "utf8": data.decode("utf-8", errors="replace")})
        else:
            values.append({"path": logical, "present": False, "byte_count": 0, "sha256": None, "utf8": None})
    return values


def actual_authority(result: ProcessResult) -> str | None:
    decisions = [item.decision.value for item in result.evidence.authorizations if item.decision is not None]
    if "DENY" in decisions:
        return "DENY"
    if len(decisions) == 2 and all(value == "ALLOW" for value in decisions):
        return "ALLOW"
    return None if result.decision is None else result.decision.value


def run_adapter(item: MaterializedScenario, scenario: RuntimeScenario) -> dict[str, object]:
    primitive = primitive_for(item.fault_injection)
    sink = EvidenceSink(item.fault_injection, primitive)
    primitive.sink = sink
    contract = TaskContract(
        item.task_contract.task_id,
        item.task_contract.description,
        [adapter_capability(item.root, cap) for cap in item.task_contract.capabilities],
    )
    adapter = ProcessAdapter(
        mapper=LogicalHostMapper(item.root.parent),
        authorizer=TaskContractPolicy(contract),
        policy_reference="EXP-015-CORPUS-2-TASK-CONTRACT",
        audit_recorder=AuditRecorder(sink),
        primitive=primitive,
    )
    request = ProcessRequest(
        item.request.session_id, item.request.task_id, item.request.request_id, item.request.actor,
        str(corpus_host_path(item.root, item.request.executable)), item.request.argv,
        adapter_cwd(item.request.cwd), item.request.timeout_ms,
    )
    started = time.perf_counter_ns()
    with parent_environment(dict(item.parent_environment)):
        result = adapter.execute(request)
    ended = time.perf_counter_ns()
    evidence = result.evidence
    events = [jsonable(event) for event in sink.events()]
    authorization = [jsonable(value) for value in evidence.authorizations]
    by_action = {value.action: value for value in evidence.authorizations}
    validation = (
        "REJECT" if "REJECTED" in {evidence.executable_validation.value, evidence.cwd_validation.value}
        else "SUCCEEDED" if evidence.executable_validation.value == evidence.cwd_validation.value == "SUCCEEDED"
        else "NOT_ATTEMPTED"
    )
    return {
        "route": item.route.value,
        "adapter_request_executable": request.executable,
        "adapter_request_cwd": request.logical_cwd,
        "canonical_executable": result.canonical_executable,
        "canonical_cwd": result.canonical_cwd,
        "exec_authorization_decision": None if "process.exec" not in by_action or by_action["process.exec"].decision is None else by_action["process.exec"].decision.value,
        "exec_authorization_rule": None if "process.exec" not in by_action else by_action["process.exec"].rule_id,
        "exec_authorization_provenance": None if "process.exec" not in by_action else jsonable(by_action["process.exec"]),
        "cwd_authorization_decision": None if "process.cwd" not in by_action or by_action["process.cwd"].decision is None else by_action["process.cwd"].decision.value,
        "cwd_authorization_rule": None if "process.cwd" not in by_action else by_action["process.cwd"].rule_id,
        "cwd_authorization_provenance": None if "process.cwd" not in by_action else jsonable(by_action["process.cwd"]),
        "compound_authorization_decision": actual_authority(result),
        "authorization_evidence": authorization,
        "validation_outcome": validation,
        "validation_reason": result.error_code if validation == "REJECT" else None,
        "executable_validation": evidence.executable_validation.value,
        "cwd_validation": evidence.cwd_validation.value,
        "spawn_attempted": evidence.spawn_attempted,
        "primitive_invocation_count": primitive.invocation_count,
        "primitive_invocations": jsonable(tuple(primitive.invocations)),
        "events_before_primitive_invocation": list(primitive.events_before_invocation),
        "child_created": evidence.child_created,
        "pid": evidence.pid,
        "child_token": evidence.child_token,
        "stdout": stream_record(evidence.stdout, result.stdout),
        "stderr": stream_record(evidence.stderr, result.stderr),
        "exit_code": result.exit_code,
        "signal": result.signal,
        "timed_out": result.timed_out,
        "term_sent": evidence.term_sent,
        "kill_sent": evidence.kill_sent,
        "fault_injection_observation": {
            "configured": jsonable(item.fault_injection),
            "audit_failure_observed": sink.failure_observed,
            "result_error_code": result.error_code,
        },
        "audit_events": events,
        "safe_error": {"code": result.error_code, "message": result.error_message},
        "terminal_classification": result.terminal_class.value,
        "result_category": result.category.value,
        "effect_possible": evidence.effect_possible,
        "timing": {"start_perf_ns": started, "end_perf_ns": ended, "total_ns": ended - started},
    }


def run_direct(item: MaterializedScenario) -> dict[str, object]:
    primitive = primitive_for(item.fault_injection)
    started = time.perf_counter_ns()
    with parent_environment(dict(item.parent_environment)):
        try:
            observation = primitive.spawn_and_wait(
                executable=str(item.executable_host_path), argv=item.request.argv,
                cwd=item.cwd_host_path, timeout_ms=item.request.timeout_ms,
            )
            error = None
        except Exception as caught:
            observation = getattr(caught, "observation", None)
            error = type(caught).__name__
    ended = time.perf_counter_ns()
    return {
        "route": item.route.value,
        "adapter_request_executable": None,
        "adapter_request_cwd": None,
        "canonical_executable": str(item.executable_host_path),
        "canonical_cwd": item.request.cwd,
        "exec_authorization_decision": None,
        "exec_authorization_rule": None,
        "exec_authorization_provenance": None,
        "cwd_authorization_decision": None,
        "cwd_authorization_rule": None,
        "cwd_authorization_provenance": None,
        "compound_authorization_decision": None,
        "authorization_evidence": [],
        "validation_outcome": "NOT_APPLICABLE_DIRECT_CONTROL",
        "validation_reason": None,
        "executable_validation": "NOT_APPLICABLE_DIRECT_CONTROL",
        "cwd_validation": "NOT_APPLICABLE_DIRECT_CONTROL",
        "spawn_attempted": primitive.invocation_count > 0,
        "primitive_invocation_count": primitive.invocation_count,
        "primitive_invocations": jsonable(tuple(primitive.invocations)),
        "events_before_primitive_invocation": [],
        "child_created": None if observation is None else observation.child_created,
        "pid": None if observation is None else observation.pid,
        "child_token": None if observation is None else observation.child_token,
        "stdout": stream_record(StreamMetadata(None, None, False, CaptureStatus.NOT_ATTEMPTED) if observation is None else observation.stdout_metadata, None if observation is None else observation.stdout),
        "stderr": stream_record(StreamMetadata(None, None, False, CaptureStatus.NOT_ATTEMPTED) if observation is None else observation.stderr_metadata, None if observation is None else observation.stderr),
        "exit_code": None if observation is None else observation.exit_code,
        "signal": None if observation is None else observation.signal,
        "timed_out": False if observation is None else observation.timed_out,
        "term_sent": False if observation is None else observation.term_sent,
        "kill_sent": False if observation is None else observation.kill_sent,
        "fault_injection_observation": {"configured": jsonable(item.fault_injection), "direct_error": error},
        "audit_events": [],
        "safe_error": {"code": error, "message": None},
        "terminal_classification": "DIRECT_CONTROL_COMPLETED" if error is None else "DIRECT_CONTROL_ERROR",
        "result_category": "DIRECT_CONTROL",
        "effect_possible": bool(observation and observation.child_created),
        "timing": {"start_perf_ns": started, "end_perf_ns": ended, "total_ns": ended - started},
    }


def execute_one(scenario: RuntimeScenario, phase: str, ordinal: int) -> dict[str, object]:
    assert_label_isolation()
    with tempfile.TemporaryDirectory(prefix="safetybox-exp015-") as directory:
        isolated_root = Path(directory)
        item = materialize(scenario, isolated_root / "workspace")
        base = {
            "run_id": "EXP-015-RUN-001",
            "runner_version": RUNNER_VERSION,
            "phase_record_kind": phase,
            "ordinal": ordinal,
            **item.raw_record_provenance(),
            "route": item.route.value,
            "session_id": item.request.session_id,
            "actor_id": item.request.actor,
            "request_id": item.request.request_id,
            "request_task_id": item.request.task_id,
            "contract_task_id": item.task_contract.task_id,
            "request_executable": item.request.executable,
            "request_argv": list(item.request.argv),
            "request_cwd": item.request.cwd,
            "timeout_ms": item.request.timeout_ms,
            "runtime_fixture": {
                "executable_kind": scenario.executable.kind.value,
                "cwd_kind": scenario.cwd.kind.value,
                "helper_behavior": None if scenario.executable.helper is None else scenario.executable.helper.value,
                "additional_object_count": len(scenario.additional_objects),
            },
            "observation_declarations": jsonable(item.observations),
            "parent_environment_keys": sorted(item.parent_environment),
        }
        observed = run_adapter(item, scenario) if item.route is Route.ADAPTER else run_direct(item)
        record = {**base, **observed}
        record["marker_observations"] = marker_observations(item)
        record["environment_observations"] = [
            {"key": key, "parent_value_sha256": sha256_bytes(item.parent_environment.get(key, "").encode()), "child_observed": None}
            for key in item.observations.environment_keys
        ]
        assert_label_isolation()
        return record


def preflight() -> list[RuntimeScenario]:
    if RUNS.exists() or REPEATS.exists() or STATE.exists():
        raise RuntimeError("EXP-015 execution artifacts already exist; one-shot will not rerun")
    if not (RESULT / "run_metadata.json").exists():
        raise RuntimeError("immutable pre-run metadata is absent")
    status = subprocess.run(("git", "status", "--porcelain=v1"), cwd=ROOT, text=True, capture_output=True, check=True).stdout.splitlines()
    if any("results/EXP-015/" not in line for line in status):
        raise RuntimeError(f"unexpected dirty worktree before run: {status}")
    assert_label_isolation()
    values = runtime_scenarios()
    # The checksum-covered JSON list is itself the frozen order. Corpus@2 uses an
    # intentionally non-numeric ordering, so no ID-derived ordering is permitted.
    return values


def main() -> None:
    scenarios = preflight()
    loaded_before = sorted(name for name in sys.modules if name.startswith("safetybox"))
    durable_json(
        STATE,
        {
            "run_id": "EXP-015-RUN-001",
            "status": "EXECUTION_STARTED_NO_PREDICTION_YET",
            "started_at": now(),
            "prediction_exposure": False,
            "loaded_modules_before_scenario_1": loaded_before,
            "prohibited_modules_loaded": [],
        },
    )
    completed = 0
    try:
        for index, scenario in enumerate(scenarios, start=1):
            record = execute_one(scenario, "CANONICAL", index)
            append_jsonl(RUNS, record)
            completed = index
            durable_json(
                STATE,
                {
                    "run_id": "EXP-015-RUN-001", "status": "EXECUTION_IN_PROGRESS",
                    "prediction_exposure": True, "canonical_records_persisted": completed,
                    "last_scenario_id": scenario.scenario_id,
                },
            )
        raw_checksum = sha256_file(RUNS)
        modules_after_raw = sorted(name for name in sys.modules if name.startswith("safetybox"))
        assert_label_isolation()
        for index, scenario_id in enumerate(REPEAT_IDS, start=1):
            scenario = next(item for item in scenarios if item.scenario_id == scenario_id)
            append_jsonl(REPEATS, execute_one(scenario, "PREREGISTERED_REPEAT", index))
        repeat_checksum = sha256_file(REPEATS)
        assert_label_isolation()
        durable_json(
            STATE,
            {
                "run_id": "EXP-015-RUN-001",
                "status": "RAW_COMPLETE_LABELS_NOT_LOADED",
                "completed_at": now(),
                "prediction_exposure": True,
                "canonical_records_persisted": completed,
                "repeat_records_persisted": len(REPEAT_IDS),
                "raw_checksum_sha256": raw_checksum,
                "repeat_checksum_sha256": repeat_checksum,
                "loaded_modules_before_scenario_1": loaded_before,
                "loaded_modules_after_120_raw_persistence": modules_after_raw,
                "prohibited_modules_loaded_before_scoring": [],
                "raw_completion_barrier": {"satisfied": completed == 120, "timestamp": now()},
                "environment_state": {
                    "python": sys.version, "platform": platform.platform(), "pid": os.getpid(),
                },
            },
        )
    except BaseException as error:
        durable_json(
            STATE,
            {
                "run_id": "EXP-015-RUN-001",
                "status": "PARTIAL_AFTER_PREDICTION_EXPOSURE" if completed else "FAILED_BEFORE_PREDICTION_EXPOSURE",
                "failed_at": now(),
                "prediction_exposure": completed > 0,
                "canonical_records_persisted": completed,
                "failure_type": type(error).__name__,
                "failure_message": str(error),
                "current_scenario_id": scenarios[completed].scenario_id if completed < len(scenarios) else None,
                "current_scenario_partial_evidence": False,
                "environment_state": {"python": sys.version, "platform": platform.platform(), "pid": os.getpid()},
            },
        )
        raise


if __name__ == "__main__":
    main()
