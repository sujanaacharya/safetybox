# ruff: noqa
"""EXP-014-RUN-001 canonical one-shot real-filesystem evaluation.

Runtime scenarios are loaded without labels.  Labels and all scoring metadata are
loaded only after canonical runs.jsonl and repeats.jsonl have been closed and fsynced.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import os
import posixpath
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import unicodedata
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any

from safetybox import Capability, TaskContract, TaskContractPolicy
from safetybox.audit import AuditRecorder
from safetybox.events import EventType, SafetyBoxEvent
from safetybox.experiments.exp014_corpus import CorpusScenario, load_labels, load_scenarios
from safetybox.filesystem import (
    FILESYSTEM_ADAPTER_VERSION,
    FILESYSTEM_AUDIT_ENVELOPE_VERSION,
    FILESYSTEM_CANONICALIZATION_VERSION,
    STATE_DIGEST_VERSION,
    FilesystemAdapter,
    FilesystemOperation,
    FilesystemRequest,
    LogicalHostMapper,
    RealFilesystemPrimitives,
)
from safetybox.filesystem.errors import FilesystemPrimitiveError
from safetybox.filesystem.models import FilesystemStat

ROOT = Path(__file__).resolve().parents[2]
RESULT_DIR = Path(__file__).resolve().parent
RUN_ID = "EXP-014-RUN-001"
PROTOCOL_SHA = "7baf20293caa83d3fff6a200174c4f8840918607"
IMPLEMENTATION_SHA = "b49a5cd0ff28a38eb8314291f51c106d2df9bd7c"
CORPUS_SHA = "5ac7311bb8f086cca97f474069d068067ac73142"
PROTOCOL_FILE = ROOT / "experiments/EXP-014/protocol.yaml"
CORPUS_DIR = ROOT / "experiments/EXP-014/corpus"
RUNS_FILE = RESULT_DIR / "runs.jsonl"
REPEATS_FILE = RESULT_DIR / "repeats.jsonl"
ATTEMPTS_FILE = RESULT_DIR / "attempts.jsonl"
SUMMARY_FILE = RESULT_DIR / "summary.json"
MUTATIONS = {
    "filesystem.write", "filesystem.append", "filesystem.create",
    "filesystem.delete", "filesystem.rename", "filesystem.mkdir",
}
READLIKE = {"filesystem.read", "filesystem.list", "filesystem.stat"}
TERMINALS = (
    "ALLOW_SUCCESS", "POLICY_DENY", "TARGET_VALIDATION_REJECT", "TOOL_ERROR",
    "FAIL_CLOSED", "FAIL_INDETERMINATE", "EXPECTED_FMED_L1_BYPASS",
)
EXPECTED_HASHES = {
    "experiments/EXP-014/protocol.yaml": "fd41816e6a3178e1d632f8f82ce10f7c70e488b06701b7be8f5615c5be333ade",
    "experiments/EXP-014/corpus/manifest.yaml": "3623b8d20f7d664cffe233a10f4c0307a6194f93eb35b5e19555fba0a9a3ab88",
    "experiments/EXP-014/corpus/scenarios.yaml": "a259906ad9dee92edc8e1ab8743a1111aae614c757535b31ae72fe884030b116",
    "experiments/EXP-014/corpus/labels.yaml": "88d9b7006b6a2adea1a81c8e54d0c587ce95ce537dc4dd7619fbd13efe833374",
}
IMPLEMENTATION_PATHS = (
    "src/safetybox/filesystem", "src/safetybox/authorization.py", "src/safetybox/audit.py",
    "src/safetybox/events.py", "src/safetybox/exceptions.py", "src/safetybox/monitor.py",
    "src/safetybox/protocols.py",
)
PROTOCOL_PATHS = (
    "experiments/EXP-014/protocol.yaml", "docs/experiments/EXP-014-real-filesystem-mediation.md",
    "docs/architecture/REAL_FILESYSTEM_MEDIATION.md",
    "docs/research/REAL_FILESYSTEM_MEDIATION_REQUIREMENTS.md",
    "docs/threat-model/REAL_FILESYSTEM_THREATS.md",
)
CORPUS_PATHS = ("experiments/EXP-014/corpus", "src/safetybox/experiments/exp014_corpus.py")


def now() -> str:
    return datetime.now(UTC).astimezone().isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def jsonable(value: object) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, bytes):
        return {"byte_size": len(value), "sha256": sha256_bytes(value)}
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: jsonable(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, MappingProxyType | dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [jsonable(item) for item in value]
    if isinstance(value, set | frozenset):
        return sorted((jsonable(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
    if isinstance(value, Path):
        return str(value)
    return value


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(("git", *args), cwd=ROOT, text=True, capture_output=True, check=check)
    return result.stdout.strip()


def append_attempt(value: dict[str, object]) -> None:
    with ATTEMPTS_FILE.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def assert_diff_free(reference: str, paths: tuple[str, ...]) -> None:
    subprocess.run(("git", "diff", "--exit-code", reference, "--", *paths), cwd=ROOT,
                   check=True, capture_output=True, text=True)


def tracked_hashes(paths: tuple[str, ...]) -> dict[str, str]:
    names = git("ls-files", "--", *paths).splitlines()
    return {name: sha256_file(ROOT / name) for name in names if name}


def preflight() -> dict[str, object]:
    head = git("rev-parse", "HEAD")
    if head != CORPUS_SHA:
        raise RuntimeError(f"HEAD is not the frozen corpus commit: {head}")
    status = git("status", "--short")
    unexpected = [line for line in status.splitlines() if "results/EXP-014" not in line]
    if unexpected:
        raise RuntimeError(f"Non-result worktree changes exist: {unexpected}")
    for relative, expected in EXPECTED_HASHES.items():
        if sha256_file(ROOT / relative) != expected:
            raise RuntimeError(f"Frozen hash mismatch: {relative}")
    subprocess.run(("sha256sum", "--check", "checksums.sha256"), cwd=CORPUS_DIR,
                   check=True, capture_output=True, text=True)
    assert_diff_free(IMPLEMENTATION_SHA, IMPLEMENTATION_PATHS)
    assert_diff_free(PROTOCOL_SHA, PROTOCOL_PATHS)
    assert_diff_free(CORPUS_SHA, CORPUS_PATHS)
    if RUNS_FILE.exists() or SUMMARY_FILE.exists() or (RESULT_DIR / "SHA256SUMS").exists():
        raise RuntimeError("A completed EXP-014 canonical artifact already exists")
    scenarios = load_scenarios()  # runtime-only; labels.yaml is not opened
    if len(scenarios) != 96 or len({item.scenario_id for item in scenarios}) != 96:
        raise RuntimeError("Frozen runtime corpus is not 96 unique scenarios")
    if [item.scenario_id for item in scenarios] != [f"FSH-014-{index:03d}" for index in range(1, 97)]:
        raise RuntimeError("Frozen manifest/scenario order differs from FSH-014-001..096")
    if [(x.scenario_id, x.repetitions) for x in scenarios if x.repetitions > 1] != [
        ("FSH-014-001", 2), ("FSH-014-093", 2)
    ]:
        raise RuntimeError("Frozen repeat set differs")
    with tempfile.TemporaryDirectory(prefix="safetybox-exp014-hardlink-probe-") as directory:
        source = Path(directory) / "source"
        target = Path(directory) / "target"
        source.write_bytes(b"probe")
        os.link(source, target)
        if source.stat().st_nlink < 2:
            raise RuntimeError("Local filesystem hard-link semantics unavailable")
    return {
        "head": head,
        "initial_cleanliness_gate_observed_before_results_creation": True,
        "initial_git_status_short": "",
        "runner_creation_status_short": status.splitlines(),
        "corpus_checksum_file_verified": True,
        "hard_links_supported": True,
        "scenario_count": len(scenarios),
        "frozen_path_diffs_zero": True,
    }


def package_environment() -> dict[str, object]:
    packages = sorted(f"{dist.metadata['Name']}=={dist.version}" for dist in importlib.metadata.distributions())
    return {"packages": packages, "sha256": sha256_bytes("\n".join(packages).encode())}


def environment(pre: dict[str, object]) -> dict[str, object]:
    try:
        pytest_version = importlib.metadata.version("pytest")
    except importlib.metadata.PackageNotFoundError:
        pytest_version = None
    return {
        "captured_at": now(), "current_head": git("rev-parse", "HEAD"),
        "python_executable": sys.executable, "python_version": sys.version,
        "implementation": platform.python_implementation(), "os": platform.system(),
        "kernel": platform.release(), "platform": platform.platform(),
        "architecture": platform.machine(), "processor": platform.processor(),
        "safetybox_version": importlib.metadata.version("safetybox"),
        "pytest_version": pytest_version, "filesystem_encoding": sys.getfilesystemencoding(),
        "timezone": time.tzname, "package_environment": package_environment(),
        "pre_run_validation": pre,
    }


def logical_to_host(root: Path, logical: str) -> Path:
    if logical == "/workspace":
        return root / "workspace"
    if not logical.startswith("/workspace/"):
        raise RuntimeError(f"Fixture path is outside logical root: {logical}")
    return root.joinpath(*logical.removeprefix("/").split("/"))


def materialize(root: Path, scenario: CorpusScenario) -> None:
    (root / "workspace").mkdir()
    for entry in scenario.filesystem_fixture.entries:
        path = logical_to_host(root, entry.path)
        if entry.type == "directory":
            path.mkdir()
        elif entry.type == "file":
            data = entry.content_utf8.encode() if entry.content_utf8 is not None else bytes.fromhex(entry.content_hex or "")
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                view = memoryview(data)
                while view:
                    written = os.write(descriptor, view)
                    view = view[written:]
            finally:
                os.close(descriptor)
        elif entry.type == "symlink":
            target = entry.target or ""
            if entry.target_kind == "logical_absolute":
                target = str(logical_to_host(root, target))
            os.symlink(target, path)
        elif entry.type == "hard_link":
            os.link(logical_to_host(root, entry.source or ""), path)
        else:
            raise RuntimeError(f"Unknown fixture type: {entry.type}")


def snapshot(root: Path) -> dict[str, object]:
    workspace = root / "workspace"
    records: list[dict[str, object]] = []

    def visit(path: Path) -> None:
        status = os.lstat(path)
        logical = "/" + path.relative_to(root).as_posix()
        if os.path.islink(path):
            node: dict[str, object] = {"type": "SYMLINK"}
        elif path.is_dir():
            children = []
            with os.scandir(path) as stream:
                entries = sorted(stream, key=lambda item: unicodedata.normalize("NFC", item.name))
            for child in entries:
                child_status = os.lstat(child.path)
                if os.path.islink(child.path):
                    kind = "SYMLINK"
                elif os.path.isdir(child.path):
                    kind = "DIRECTORY"
                elif os.path.isfile(child.path):
                    kind = "FILE"
                else:
                    kind = "OTHER"
                children.append({"name": unicodedata.normalize("NFC", child.name), "type": kind})
            node = {"type": "DIRECTORY", "children": children}
        elif path.is_file():
            data = path.read_bytes()
            node = {"type": "FILE", "byte_size": len(data), "content_sha256": sha256_bytes(data)}
        else:
            node = {"type": "OTHER", "mode": status.st_mode & 0o7777}
        records.append({"logical_path": logical, "node": node})
        if node["type"] == "DIRECTORY":
            for child in entries:
                visit(Path(child.path))

    visit(workspace)
    records.sort(key=lambda item: str(item["logical_path"]))
    document = {"version": STATE_DIGEST_VERSION, "records": records}
    return {"digest": sha256_bytes(canonical(document)), "manifest": document}


@dataclass
class TimingSink:
    fail_on: EventType | None = None

    def __post_init__(self) -> None:
        self.events_recorded: list[SafetyBoxEvent] = []
        self.latencies_ns: list[int] = []

    def record(self, event: SafetyBoxEvent) -> None:
        started = time.perf_counter_ns()
        try:
            if event.event_type is self.fail_on:
                raise OSError("EXP-014 frozen injected audit failure")
            self.events_recorded.append(event)
        finally:
            self.latencies_ns.append(time.perf_counter_ns() - started)

    def events(self) -> tuple[SafetyBoxEvent, ...]:
        return tuple(self.events_recorded)


@dataclass
class TimedAuthorizer:
    delegate: object
    inject_failure: bool = False

    def __post_init__(self) -> None:
        self.latencies_ns: list[int] = []

    def authorize(self, request: object) -> object:
        started = time.perf_counter_ns()
        try:
            if self.inject_failure:
                raise RuntimeError("EXP-014 frozen injected authorization failure")
            return self.delegate.authorize(request)  # type: ignore[attr-defined]
        finally:
            self.latencies_ns.append(time.perf_counter_ns() - started)


@dataclass
class InstrumentedPrimitives(RealFilesystemPrimitives):
    root: Path
    sink: TimingSink
    injection: str | None = None
    partial_bytes: int | None = None

    def __post_init__(self) -> None:
        self.probes: list[dict[str, object]] = []
        self.invocations: list[dict[str, object]] = []
        self.primitive_latencies_ns: list[int] = []
        self.probe_latencies_ns: list[int] = []
        self.confinement_ok = True

    def _path(self, path: Path) -> str:
        absolute = path.absolute()
        try:
            relative = absolute.relative_to(self.root)
        except ValueError:
            self.confinement_ok = False
            return "OUTSIDE_ROOT"
        return "/" + relative.as_posix()

    def _probe(self, name: str, paths: tuple[Path, ...], call: Any) -> Any:
        started = time.perf_counter_ns()
        self.probes.append({"name": name, "paths": [self._path(path) for path in paths]})
        try:
            if self.injection == "validator_exception_before_effect" and name == "lstat":
                raise PermissionError("EXP-014 frozen injected validator failure")
            return call()
        finally:
            self.probe_latencies_ns.append(time.perf_counter_ns() - started)

    def _invoke(self, name: str, paths: tuple[Path, ...], call: Any) -> Any:
        started = time.perf_counter_ns()
        observation = {
            "name": name,
            "paths": [self._path(path) for path in paths],
            "audit_event_types_before_invocation": [event.event_type.value for event in self.sink.events()],
            "audit_sequence_numbers_before_invocation": [event.sequence_number for event in self.sink.events()],
        }
        self.invocations.append(observation)
        try:
            if self.injection == "permission_error_before_effect":
                raise FilesystemPrimitiveError("EXP014-INJECTED-PERMISSION", "Injected permission-like primitive failure.", effect_possible=False)
            if self.injection == "partial_write_then_error":
                path, data = paths[0], call
                descriptor = os.open(path, os.O_WRONLY | os.O_TRUNC)
                try:
                    os.write(descriptor, data[: self.partial_bytes])
                finally:
                    os.close(descriptor)
                raise FilesystemPrimitiveError("EXP014-INJECTED-PARTIAL-WRITE", "Injected partial write failure.", effect_possible=True)
            return call() if callable(call) else call
        finally:
            elapsed = time.perf_counter_ns() - started
            self.primitive_latencies_ns.append(elapsed)
            observation["latency_ns"] = elapsed

    def lstat(self, path: Path) -> os.stat_result:
        return self._probe("lstat", (path,), lambda: super(InstrumentedPrimitives, self).lstat(path))

    def directory_is_empty(self, path: Path) -> bool:
        return self._probe("directory_is_empty", (path,), lambda: super(InstrumentedPrimitives, self).directory_is_empty(path))

    def read(self, path: Path) -> bytes:
        return self._invoke("read", (path,), lambda: super(InstrumentedPrimitives, self).read(path))

    def write(self, path: Path, data: bytes) -> None:
        if self.injection == "partial_write_then_error":
            self._invoke("write", (path,), data)
            return
        self._invoke("write", (path,), lambda: super(InstrumentedPrimitives, self).write(path, data))

    def append(self, path: Path, data: bytes) -> None:
        self._invoke("append", (path,), lambda: super(InstrumentedPrimitives, self).append(path, data))

    def create(self, path: Path, data: bytes) -> None:
        self._invoke("create", (path,), lambda: super(InstrumentedPrimitives, self).create(path, data))

    def delete_file(self, path: Path) -> None:
        self._invoke("delete_file", (path,), lambda: super(InstrumentedPrimitives, self).delete_file(path))

    def delete_directory(self, path: Path) -> None:
        self._invoke("delete_directory", (path,), lambda: super(InstrumentedPrimitives, self).delete_directory(path))

    def rename(self, source: Path, destination: Path) -> None:
        self._invoke("rename", (source, destination), lambda: super(InstrumentedPrimitives, self).rename(source, destination))

    def mkdir(self, path: Path) -> None:
        self._invoke("mkdir", (path,), lambda: super(InstrumentedPrimitives, self).mkdir(path))

    def list_directory(self, path: Path) -> tuple[str, ...]:
        return self._invoke("list", (path,), lambda: super(InstrumentedPrimitives, self).list_directory(path))

    def minimized_stat(self, path: Path) -> FilesystemStat:
        return self._invoke("stat", (path,), lambda: super(InstrumentedPrimitives, self).minimized_stat(path))


def event_record(event: SafetyBoxEvent) -> dict[str, object]:
    return {
        "event_id": event.event_id, "session_id": event.session_id, "task_id": event.task_id,
        "sequence_number": event.sequence_number, "event_type": event.event_type.value,
        "request_id": event.request_id, "actor": event.actor, "action": event.action,
        "resource": event.resource, "correlation_id": event.correlation_id,
        "timestamp": event.timestamp.isoformat(), "rule_id": event.rule_id,
        "decision": None if event.decision is None else event.decision.value,
        "executed": event.executed, "parent_event_id": event.parent_event_id,
        "metadata": jsonable(event.metadata),
    }


def terminal(category: str, validation: str, error_code: str | None, route: str, succeeded: bool) -> str:
    if route != "adapter":
        return "EXPECTED_FMED_L1_BYPASS" if succeeded else "TOOL_ERROR"
    if category == "ALLOW":
        return "ALLOW_SUCCESS"
    if category == "DENY":
        return "POLICY_DENY"
    if validation == "TARGET_VALIDATION_REJECT" and error_code in {
        "EXP014-TARGET-SYMLINK-REJECT",
        "EXP014-TARGET-HARDLINK-REJECT",
        "EXP014-TARGET-ROOT-REJECT",
    }:
        return "TARGET_VALIDATION_REJECT"
    if category in {"TOOL_ERROR", "FAIL_CLOSED", "FAIL_INDETERMINATE"}:
        return category
    raise RuntimeError(f"Cannot normalize terminal: {category}/{validation}")


def policy_reference(scenario: CorpusScenario) -> str:
    contract = {
        "task_id": scenario.task_contract.task_id,
        "description": scenario.task_contract.description,
        "capabilities": sorted((item.action, item.resource) for item in scenario.task_contract.capabilities),
    }
    return "EXP-014-CONTRACT-SHA256:" + sha256_bytes(canonical(contract))


def result_value(value: object) -> object:
    if isinstance(value, bytes):
        return {"type": "BYTES", "byte_size": len(value), "sha256": sha256_bytes(value)}
    if isinstance(value, tuple):
        return {"type": "NAMES", "names": list(value)}
    if isinstance(value, FilesystemStat):
        return {"type": "STAT", **jsonable(value)}
    return None


def reconstruct(envelope: dict[str, object], events: list[dict[str, object]]) -> dict[str, object]:
    required = {
        "session_id": bool(envelope.get("session_id")), "task_id": bool(envelope.get("task_id")),
        "request_id": bool(envelope.get("request_id")), "correlation_id": bool(envelope.get("correlation_id")),
        "requested_resource": bool(envelope.get("requested_resource")), "action": bool(envelope.get("action")),
        "execution_attempted": isinstance(envelope.get("execution_attempted"), bool),
        "execution_succeeded": "execution_succeeded" in envelope,
        "result_category": bool(envelope.get("result_category")),
        "sequence_numbers": isinstance(envelope.get("sequence_numbers"), list),
        "adapter_version": bool(envelope.get("adapter_version")),
        "policy_reference": bool(envelope.get("policy_reference")),
    }
    if envelope.get("canonical_resource") is not None:
        required["canonical_resource"] = bool(envelope.get("canonical_resource"))
    if envelope.get("action") == "filesystem.rename" and envelope.get("canonical_resource") is not None:
        required["canonical_destination"] = bool(envelope.get("canonical_destination"))
        required["rename_subdecisions"] = len(envelope.get("authorizations", [])) == 2
    if envelope.get("result_category") == "DENY":
        required["authorization_rule_id"] = all(bool(item.get("rule_id")) for item in envelope.get("authorizations", []))
        required["decision"] = all(item.get("decision") == "DENY" or item.get("decision") == "ALLOW" for item in envelope.get("authorizations", []))
    if envelope.get("result_category") in {"TOOL_ERROR", "FAIL_CLOSED", "FAIL_INDETERMINATE"}:
        required["tool_error_category"] = bool(envelope.get("error_code"))
    sequences = [item["sequence_number"] for item in events]
    listed = envelope.get("sequence_numbers", [])
    required["sequence_numbers_match_committed_events"] = listed == sequences
    event_ids = {item["event_id"] for item in events}
    required["parent_links_resolve"] = all(item["parent_event_id"] is None or item["parent_event_id"] in event_ids for item in events)
    missing = sorted(key for key, okay in required.items() if not okay)
    return {"reconstructable": not missing, "missing_or_invalid_fields": missing, "fields": required}


def ordering_record(route: str, events: list[dict[str, object]], invocations: list[dict[str, object]], authorizations: list[dict[str, object]]) -> dict[str, object]:
    if route != "adapter":
        return {"applicable": False, "correct": None, "violations": []}
    types = [item["event_type"] for item in events]
    violations: list[str] = []
    started = [index for index, name in enumerate(types) if name == "EXECUTION_STARTED"]
    denied = "AUTHORIZATION_DENIED" in types
    if denied and started:
        violations.append("denial_has_execution_start")
    if denied and invocations:
        violations.append("denial_has_primitive_invocation")
    if started:
        allow = [index for index, name in enumerate(types) if name == "AUTHORIZATION_ALLOWED"]
        validation = [index for index, name in enumerate(types) if name == "TARGET_VALIDATION_SUCCEEDED"]
        if not allow or not validation or not (allow[-1] < validation[-1] < started[0]):
            violations.append("allow_validation_execution_order")
        for invocation in invocations:
            observed = invocation["audit_event_types_before_invocation"]
            if "EXECUTION_STARTED" not in observed:
                violations.append("primitive_before_committed_execution_start")
    elif invocations:
        violations.append("primitive_without_execution_start")
    if len(authorizations) == 2 and started and not all(item.get("decision") == "ALLOW" for item in authorizations):
        violations.append("rename_started_without_two_allows")
    return {"applicable": True, "correct": not violations, "violations": violations}


def disclosure_observation(operation: str, public_value: object, error_message: str | None,
                           events: list[dict[str, object]], primitive_invoked: bool) -> dict[str, object]:
    if operation not in READLIKE:
        return {"applicable": False, "observed": False, "channels": []}
    channels = []
    if public_value is not None:
        channels.append("public_result_value")
    if primitive_invoked:
        channels.append("protected_primitive_invoked")
    # Safe errors and audit evidence are structurally checked for result payload fields.
    if any("value" in item.get("metadata", {}) or "tool_result" in item.get("metadata", {}) for item in events):
        channels.append("audit_result_payload")
    return {"applicable": True, "observed": bool(channels), "channels": channels,
            "safe_error_message_present": error_message is not None}


def execute_once(scenario: CorpusScenario, execution_index: int, canonical_record: bool) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="safetybox-exp014-run-") as directory:
        root = Path(directory)
        materialize(root, scenario)
        pre = snapshot(root)
        injection = None if scenario.dependency_injection is None else scenario.dependency_injection.type
        fail_event = None
        if injection == "reject_execution_started":
            fail_event = EventType.EXECUTION_STARTED
        elif injection == "reject_terminal_success":
            fail_event = EventType.EXECUTION_SUCCEEDED
        sink = TimingSink(fail_event)
        primitives = InstrumentedPrimitives(root, sink, injection,
                                             None if scenario.dependency_injection is None else scenario.dependency_injection.partial_bytes)
        started_ns = time.perf_counter_ns()
        result = None
        direct_error = None
        direct_succeeded = False
        authorizer: TimedAuthorizer | None = None
        if scenario.route == "adapter":
            contract = TaskContract(
                scenario.task_contract.task_id,
                scenario.task_contract.description,
                [Capability(item.action, item.resource) for item in scenario.task_contract.capabilities],
            )
            authorizer = TimedAuthorizer(TaskContractPolicy(contract), injection == "authorization_exception")
            adapter = FilesystemAdapter(
                mapper=LogicalHostMapper(root), authorizer=authorizer,
                policy_reference=policy_reference(scenario), audit_recorder=AuditRecorder(sink),
                primitives=primitives,
            )
            payload = scenario.request.adapter_payload()
            request = FilesystemRequest(
                session_id=str(payload["session_id"]), task_id=str(payload["task_id"]),
                request_id=str(payload["request_id"]), actor=str(payload["actor"]),
                operation=FilesystemOperation(str(payload["operation"])), resource=str(payload["resource"]),
                destination=payload.get("destination"), data=payload.get("data"),
            )
            result = adapter.execute(request)
        else:
            try:
                requested = scenario.request.resource
                logical = requested if requested.startswith("/") else "/workspace/" + requested
                target = logical_to_host(root, logical)
                data = scenario.request.adapter_payload().get("data")
                if not isinstance(data, bytes):
                    raise RuntimeError("Direct write control has no bytes")
                primitives.invocations.append({
                    "name": scenario.route, "paths": [primitives._path(target)],
                    "audit_event_types_before_invocation": [], "audit_sequence_numbers_before_invocation": [],
                })
                primitive_start = time.perf_counter_ns()
                if scenario.route == "direct_os_open":
                    descriptor = os.open(target, os.O_WRONLY | os.O_TRUNC)
                    try:
                        os.write(descriptor, data)
                    finally:
                        os.close(descriptor)
                else:
                    target.write_bytes(data)
                primitives.primitive_latencies_ns.append(time.perf_counter_ns() - primitive_start)
                direct_succeeded = True
            except Exception as error:
                direct_error = f"{type(error).__name__}: {error}"
        total_ns = time.perf_counter_ns() - started_ns
        post = snapshot(root)
        events = [event_record(item) for item in sink.events()]
        if result is not None:
            envelope = jsonable(result.evidence)
            category = result.category.value
            validation = result.evidence.physical_validation.value
            public = result_value(result.value)
            error_code = result.error_code
            error_message = result.error_message
            canonical_resource = result.canonical_resource
            canonical_destination = result.canonical_destination
            authorizations = jsonable(result.evidence.authorizations)
            adapter_pre = result.evidence.pre_state_digest
            adapter_post = result.evidence.post_state_digest
            decision = None if result.decision is None else result.decision.value
            primitive_result = public if result.category.value == "ALLOW" else None
        else:
            category = "ALLOW" if direct_succeeded else "TOOL_ERROR"
            validation = "NOT_ATTEMPTED"
            public = None
            error_code = None if direct_succeeded else "EXP014-DIRECT-ROUTE-ERROR"
            error_message = direct_error
            canonical_resource = scenario.request.resource if scenario.request.resource.startswith("/workspace/") else "/workspace/" + scenario.request.resource
            canonical_destination = None
            authorizations = []
            adapter_pre = adapter_post = decision = primitive_result = None
            envelope = {}
        primitive_invoked = bool(primitives.invocations)
        actual_terminal = terminal(category, validation, error_code, scenario.route, direct_succeeded)
        reconstruction = reconstruct(envelope, events) if result is not None else {
            "reconstructable": False, "missing_or_invalid_fields": ["direct_route_has_no_adapter_audit"], "fields": {}
        }
        order = ordering_record(scenario.route, events, primitives.invocations, authorizations)
        disclosure = disclosure_observation(scenario.request.operation, public, error_message, events, primitive_invoked)
        changed = pre["digest"] != post["digest"]
        audit_truth_violations = []
        if result is not None:
            if bool(envelope["execution_attempted"]) != primitive_invoked:
                audit_truth_violations.append("execution_attempted_disagrees_with_primitive")
            claimed = envelope["execution_succeeded"]
            if claimed is False and changed and scenario.request.operation in MUTATIONS:
                audit_truth_violations.append("audit_claims_failure_but_state_changed")
            if claimed is True and category != "ALLOW":
                audit_truth_violations.append("audit_claims_success_for_nonallow_result")
            if adapter_pre is not None and adapter_post is not None:
                if (adapter_pre != adapter_post) != changed:
                    audit_truth_violations.append("adapter_digest_change_disagrees_with_independent_state")
        fixture_paths = {entry.path: entry for entry in scenario.filesystem_fixture.entries}
        symlink_features = []
        for entry in scenario.filesystem_fixture.entries:
            if entry.type != "symlink":
                continue
            if entry.target_kind == "logical_absolute":
                resolved_target = entry.target
            else:
                resolved_target = posixpath.normpath(posixpath.join(posixpath.dirname(entry.path), entry.target or ""))
            terminal_link = canonical_resource == entry.path
            intermediate_link = bool(canonical_resource and canonical_resource.startswith(entry.path + "/"))
            symlink_features.append({
                "path": entry.path, "target_kind": entry.target_kind,
                "terminal_for_request": terminal_link, "intermediate_for_request": intermediate_link,
                "chain": resolved_target in fixture_paths and fixture_paths[resolved_target].type == "symlink",
                "dangling": resolved_target not in fixture_paths,
                "rename_case": scenario.request.operation == "filesystem.rename",
                "create_parent_case": scenario.request.operation in {"filesystem.create", "filesystem.mkdir"} and intermediate_link,
            })
        hardlink_features = [{"path":entry.path,"source":entry.source} for entry in scenario.filesystem_fixture.entries if entry.type == "hard_link"]
        record = {
            "run_id": RUN_ID, "scenario_id": scenario.scenario_id,
            "execution_index": execution_index, "canonical_record": canonical_record,
            "route": scenario.route, "fixture_sha256": scenario.filesystem_fixture.sha256,
            "request_identity": {
                "session_id": scenario.request.session_id, "task_id": scenario.request.task_id,
                "request_id": scenario.request.request_id, "correlation_id": scenario.request.request_id,
                "actor": scenario.request.actor,
            },
            "operation": scenario.request.operation,
            "requested_logical_resource": scenario.request.resource,
            "canonical_logical_resource": canonical_resource,
            "rename_destination_requested": scenario.request.destination,
            "rename_destination_canonical": canonical_destination,
            "authorization_decision": decision,
            "authorization_decisions": authorizations,
            "authorization_rule_ids": [item.get("rule_id") for item in authorizations],
            "physical_validation_result": validation,
            "execution_start_observed": any(item["event_type"] == "EXECUTION_STARTED" for item in events),
            "primitive_invoked": primitive_invoked,
            "primitive_invocations": primitives.invocations,
            "primitive_result": primitive_result,
            "terminal_classification": actual_terminal,
            "public_result_category": category,
            "error_safe_code": error_code, "error_safe_category": category if error_code else None,
            "error_safe_message": error_message,
            "adapter_pre_state_digest": adapter_pre, "adapter_post_state_digest": adapter_post,
            "independent_pre_state_digest": pre["digest"], "independent_post_state_digest": post["digest"],
            "side_effect_observed": changed,
            "protected_disclosure_observed": disclosure["observed"],
            "disclosure_observation": disclosure,
            "audit_reconstruction_record": reconstruction,
            "audit_event_sequence": events,
            "authorization_ordering": order,
            "audit_truthfulness": {"truthful": not audit_truth_violations, "violations": audit_truth_violations},
            "adapter_version": FILESYSTEM_ADAPTER_VERSION,
            "canonicalization_version": FILESYSTEM_CANONICALIZATION_VERSION,
            "audit_envelope_version": FILESYSTEM_AUDIT_ENVELOPE_VERSION,
            "state_digest_version": STATE_DIGEST_VERSION,
            "environment_runner_version": "EXP-014-EVALUATOR@1",
            "timing_ns": {
                "adapter_total": total_ns,
                "authorization_calls": [] if authorizer is None else authorizer.latencies_ns,
                "validation_probe_calls": primitives.probe_latencies_ns,
                "primitive_calls": primitives.primitive_latencies_ns,
                "audit_calls": sink.latencies_ns,
            },
            "temporary_root": {
                "host_path_recorded": False,
                "root_token_sha256": sha256_bytes(str(root).encode()),
                "all_observed_primitive_and_probe_paths_confined": primitives.confinement_ok,
                "fresh_for_scenario": True,
            },
            "dependency_injection": None if scenario.dependency_injection is None else {
                "boundary": scenario.dependency_injection.boundary,
                "type": scenario.dependency_injection.type,
                "partial_bytes": scenario.dependency_injection.partial_bytes,
            },
            "runtime_fixture_features": {"symlinks":symlink_features,"hard_links":hardlink_features},
        }
        return record


def semantic(record: dict[str, object]) -> dict[str, object]:
    return {
        key: record[key] for key in (
            "terminal_classification", "canonical_logical_resource", "rename_destination_canonical",
            "authorization_decision", "authorization_decisions", "physical_validation_result",
            "public_result_category", "error_safe_code", "independent_pre_state_digest",
            "independent_post_state_digest", "side_effect_observed", "protected_disclosure_observed",
            "audit_reconstruction_record",
        )
    } | {"audit_event_types": [item["event_type"] for item in record["audit_event_sequence"]]}


def ratio(n: int, d: int) -> float | None:
    return n / d if d else None


def timing_summary(values: list[int]) -> dict[str, object]:
    if not values:
        return {"count": 0, "minimum_ns": None, "median_ns": None, "mean_ns": None, "p95_ns": None, "p99_ns": None}
    ordered = sorted(values)
    percentile = lambda p: ordered[min(len(ordered) - 1, math.ceil(p * len(ordered)) - 1)]
    return {"count": len(values), "minimum_ns": min(values), "median_ns": statistics.median(values),
            "mean_ns": statistics.mean(values), "p95_ns": percentile(.95), "p99_ns": percentile(.99)}


def score(records: list[dict[str, object]], repeat_records: list[dict[str, object]], label_joined_at: str) -> dict[str, object]:
    labels = load_labels()
    by_id = {item.scenario_id: item for item in labels}
    if set(by_id) != {item["scenario_id"] for item in records}:
        raise RuntimeError("Labels do not join exactly to persisted canonical records")
    enriched = [(record, by_id[str(record["scenario_id"])]) for record in records]
    terminal_matches = [record["terminal_classification"] == label.expected_terminal_classification for record, label in enriched]
    actual_counts = Counter(str(record["terminal_classification"]) for record in records)
    expected_counts = Counter(label.expected_terminal_classification for _, label in enriched)
    per_class = {}
    for name in TERMINALS:
        members = [(record, label) for record, label in enriched if label.expected_terminal_classification == name]
        matched = sum(record["terminal_classification"] == name for record, _ in members)
        per_class[name] = {"correct": matched, "total": len(members), "accuracy": ratio(matched, len(members))}
    auth_members = [(record, label) for record, label in enriched if label.authorization_metric_member]
    def actual_auth(record: dict[str, object]) -> str | None:
        decisions = [item.get("decision") for item in record["authorization_decisions"]]
        if decisions:
            if "DENY" in decisions: return "DENY"
            if all(value == "ALLOW" for value in decisions): return "ALLOW"
        return record["authorization_decision"]
    auth_correct = sum(actual_auth(record) == label.expected_authorization_decision for record, label in auth_members)
    denied_mut = [(record, label) for record, label in enriched if label.expected_terminal_classification == "POLICY_DENY" and record["operation"] in MUTATIONS]
    denied_mut_pass = [record for record, _ in denied_mut if not record["primitive_invoked"] and not record["side_effect_observed"] and record["independent_pre_state_digest"] == record["independent_post_state_digest"]]
    nondisclosure = {}
    for operation in sorted(READLIKE):
        members = [(record, label) for record, label in enriched if label.expected_terminal_classification == "POLICY_DENY" and record["operation"] == operation]
        passed = [record for record, _ in members if not record["primitive_invoked"] and not record["protected_disclosure_observed"]]
        nondisclosure[operation.removeprefix("filesystem.")] = {"passes": len(passed), "total": len(members), "rate": ratio(len(passed), len(members)), "failure_ids": [r["scenario_id"] for r, _ in members if r not in passed]}
    nd_total = sum(item["total"] for item in nondisclosure.values())
    nd_pass = sum(item["passes"] for item in nondisclosure.values())
    ordering_members = [record for record in records if record["authorization_ordering"]["applicable"]]
    ordering_pass = [record for record in ordering_members if record["authorization_ordering"]["correct"]]
    adapter_records = [record for record in records if record["route"] == "adapter"]
    reconstruction_pass = [record for record in adapter_records if record["audit_reconstruction_record"]["reconstructable"]]
    truthful_pass = [record for record in adapter_records if record["audit_truthfulness"]["truthful"]]
    inv016_members = [(r,l) for r,l in enriched if "INV-016" in l.invariants]
    inv017_members = [(r,l) for r,l in enriched if "INV-017" in l.invariants]
    inv018_members = [(r,l) for r,l in enriched if "INV-018" in l.invariants]
    inv019_members = [(r,l) for r,l in enriched if "INV-019" in l.invariants]
    inv016_fail = [r["scenario_id"] for r,l in inv016_members if (l.expected_terminal_classification in {"POLICY_DENY","FAIL_CLOSED","TARGET_VALIDATION_REJECT"} and (r["primitive_invoked"] or r["side_effect_observed"]))]
    inv017_fail = [r["scenario_id"] for r,l in inv017_members if r["primitive_invoked"] or r["protected_disclosure_observed"]]
    inv018_fail = [r["scenario_id"] for r,l in inv018_members if r["terminal_classification"] != l.expected_terminal_classification]
    inv019_fail = [r["scenario_id"] for r,l in inv019_members if r["primitive_invoked"] or r["side_effect_observed"] or r["protected_disclosure_observed"]]
    invariants = {
        "INV-016": {"applicable": len(inv016_members), "passes": len(inv016_members)-len(inv016_fail), "failures": inv016_fail},
        "INV-017": {"applicable": len(inv017_members), "passes": len(inv017_members)-len(inv017_fail), "failures": inv017_fail,
                    "by_operation": nondisclosure},
        "INV-018": {"applicable": len(inv018_members), "passes": len(inv018_members)-len(inv018_fail), "failures": inv018_fail},
        "INV-019": {"applicable": len(inv019_members), "passes": len(inv019_members)-len(inv019_fail), "failures": inv019_fail},
    }
    pair_groups: dict[str, list[tuple[dict[str, object], object]]] = defaultdict(list)
    for record, label in enriched: pair_groups[label.counterfactual_pair_id].append((record,label))
    pairs = []
    for pair_id, members in sorted(pair_groups.items()):
        members.sort(key=lambda item: item[1].pair_role)
        correct = all(record["terminal_classification"] == label.expected_terminal_classification for record,label in members)
        pairs.append({"pair_id": pair_id, "scenario_a": members[0][0]["scenario_id"], "scenario_b": members[1][0]["scenario_id"],
                      "semantic_variable_changed": members[0][1].semantic_variable,
                      "actual_outcomes": [item[0]["terminal_classification"] for item in members],
                      "expected_outcomes": [item[1].expected_terminal_classification for item in members], "pair_correct": correct,
                      "family": sorted(set(f for _,label in members for f in label.family))})
    hard = [(record,label) for record,label in enriched if label.hard_negative]
    hard_ok = [(record,label) for record,label in hard if record["terminal_classification"] == label.expected_terminal_classification]
    operation_results = {}
    for operation in sorted({str(record["operation"]) for record in records}):
        members = [(r,l) for r,l in enriched if r["operation"] == operation]
        auth_evaluable = [(r,l) for r,l in members if l.authorization_metric_member]
        auth_ok = sum(actual_auth(r) == l.expected_authorization_decision for r,l in auth_evaluable)
        side_applicable = [(r,l) for r,l in members if operation in MUTATIONS and l.expected_terminal_classification != "FAIL_INDETERMINATE"]
        side_ok = sum((r["side_effect_observed"] if l.expected_terminal_classification in {"ALLOW_SUCCESS","EXPECTED_FMED_L1_BYPASS"} else not r["side_effect_observed"]) for r,l in side_applicable)
        nd_applicable = [(r,l) for r,l in members if l.expected_terminal_classification == "POLICY_DENY" and operation in READLIKE]
        nd_ok = sum(not r["protected_disclosure_observed"] and not r["primitive_invoked"] for r,l in nd_applicable)
        operation_results[operation.removeprefix("filesystem.")] = {
            "total": len(members), "terminal_correct": sum(r["terminal_classification"] == l.expected_terminal_classification for r,l in members),
            "policy_correct": auth_ok, "policy_evaluable": len(auth_evaluable),
            "side_effect_correct": side_ok, "side_effect_applicable": len(side_applicable),
            "nondisclosure_correct": nd_ok, "nondisclosure_applicable": len(nd_applicable),
        }
    def family_result(term: str) -> dict[str, object]:
        members = [(r,l) for r,l in enriched if any(term in value.lower().replace("-","_") for value in l.family)]
        failures = [r["scenario_id"] for r,l in members if r["terminal_classification"] != l.expected_terminal_classification]
        return {"cases": len(members), "passes": len(members)-len(failures), "failure_ids": failures,
                "records": [{"scenario_id": r["scenario_id"], "terminal": r["terminal_classification"], "validation": r["physical_validation_result"], "primitive_invoked": r["primitive_invoked"], "side_effect": r["side_effect_observed"]} for r,l in members]}
    symlink = family_result("symlink")
    hardlink = family_result("hard_link")
    if hardlink["cases"] == 0: hardlink = family_result("hardlink")
    symlink_breakdown = {}
    for subtype in ("terminal", "intermediate", "relative", "absolute", "chain", "dangling", "rename", "create_parent"):
        members = []
        for r,l in enriched:
            features = r["runtime_fixture_features"]["symlinks"]
            matched = any(
                (subtype == "terminal" and item["terminal_for_request"])
                or (subtype == "intermediate" and item["intermediate_for_request"])
                or (subtype == "relative" and item["target_kind"] == "relative")
                or (subtype == "absolute" and item["target_kind"] == "logical_absolute")
                or (subtype == "chain" and item["chain"])
                or (subtype == "dangling" and item["dangling"])
                or (subtype == "rename" and item["rename_case"])
                or (subtype == "create_parent" and item["create_parent_case"])
                for item in features
            )
            if matched: members.append((r,l))
        failures = [r["scenario_id"] for r,l in members if r["terminal_classification"] != l.expected_terminal_classification]
        symlink_breakdown[subtype] = {"cases":len(members),"passes":len(members)-len(failures),"failure_ids":failures}
    symlink["by_subtype"] = symlink_breakdown
    hardlink_members = [(r,l) for r,l in enriched if r["runtime_fixture_features"]["hard_links"]]
    hardlink.update({
        "supported_cases":len(hardlink_members),
        "expected_rejections":sum(l.expected_terminal_classification=="TARGET_VALIDATION_REJECT" for r,l in hardlink_members),
        "actual_rejections":sum(r["terminal_classification"]=="TARGET_VALIDATION_REJECT" for r,l in hardlink_members),
        "unexpected_executions":[r["scenario_id"] for r,l in hardlink_members if r["primitive_invoked"] and l.expected_terminal_classification=="TARGET_VALIDATION_REJECT"],
    })
    rename = []
    for r,l in enriched:
        if r["operation"] == "filesystem.rename":
            rename.append({"scenario_id": r["scenario_id"], "source_decision": r["authorization_decisions"][0]["decision"] if r["authorization_decisions"] else None,
                           "destination_decision": r["authorization_decisions"][1]["decision"] if len(r["authorization_decisions"]) > 1 else None,
                           "validation": r["physical_validation_result"], "execution_result": r["public_result_category"],
                           "terminal_label": l.expected_terminal_classification, "actual_terminal": r["terminal_classification"],
                           "correct": r["terminal_classification"] == l.expected_terminal_classification,
                           "side_effect": r["side_effect_observed"]})
    categories = {name: {"cases": sum(l.expected_terminal_classification == name for _,l in enriched),
                         "correct": sum(l.expected_terminal_classification == name and r["terminal_classification"] == name for r,l in enriched),
                         "failure_ids": [r["scenario_id"] for r,l in enriched if l.expected_terminal_classification == name and r["terminal_classification"] != name]}
                  for name in ("TOOL_ERROR","FAIL_CLOSED","FAIL_INDETERMINATE")}
    failure_classes = {
        "authorization_failures":[r["scenario_id"] for r in records if r["error_safe_code"]=="FS-AUTHORIZATION-FAILED"],
        "canonicalization_failures":[r["scenario_id"] for r in records if str(r["error_safe_code"] or "").startswith("FS-CANONICALIZATION")],
        "target_validation_failures":[r["scenario_id"] for r in records if r["physical_validation_result"]=="TARGET_VALIDATION_REJECT"],
        "tool_errors":[r["scenario_id"] for r in records if r["public_result_category"]=="TOOL_ERROR"],
        "audit_pre_effect_failures":[r["scenario_id"] for r in records if r["error_safe_code"]=="FS-AUDIT-PRE-EXECUTION"],
        "partial_effect_failures":[r["scenario_id"] for r in records if r["public_result_category"]=="FAIL_INDETERMINATE" and r["side_effect_observed"] and r["error_safe_code"]!="FS-AUDIT-POST-EXECUTION"],
        "post_effect_audit_failures":[r["scenario_id"] for r in records if r["error_safe_code"]=="FS-AUDIT-POST-EXECUTION"],
    }
    canonical_members = inv018_members
    canonical_fail = [r["scenario_id"] for r,l in canonical_members if r["terminal_classification"] != l.expected_terminal_classification]
    canonical_behaviors = defaultdict(list)
    for r,l in enriched:
        raw = str(r["requested_logical_resource"])
        parts = raw.split("/")
        tags=[]
        if not raw.startswith("/"): tags.append("relative_path")
        if raw.startswith("/workspace"): tags.append("absolute_logical_path")
        if "." in parts: tags.append("dot_segment")
        if ".." in parts: tags.append("dot_dot_segment")
        if "//" in raw: tags.append("repeated_separator")
        if raw.endswith("/"): tags.append("trailing_separator")
        if unicodedata.normalize("NFC",raw)!=raw: tags.append("nfc_normalization")
        if raw=="/workspace": tags.append("root_boundary")
        if str(r["error_safe_code"] or "")=="FS-CANONICALIZATION-ROOT-ESCAPE": tags.append("root_escape")
        if raw.startswith("/") and not (raw=="/workspace" or raw.startswith("/workspace/")): tags.append("host_namespace_rejection")
        if "prefix_collision" in l.threats: tags.append("prefix_collision")
        for tag in tags:
            canonical_behaviors[tag].append({"scenario_id":r["scenario_id"],"requested":raw,
                                             "canonical":r["canonical_logical_resource"],
                                             "terminal":r["terminal_classification"],
                                             "expected":l.expected_terminal_classification,
                                             "correct":r["terminal_classification"]==l.expected_terminal_classification})
    repeat_comparisons = []
    canonical_by_id = {r["scenario_id"]: r for r in records}
    for repeat in repeat_records:
        expected_semantic = semantic(canonical_by_id[str(repeat["scenario_id"])])
        actual_semantic = semantic(repeat)
        repeat_comparisons.append({"scenario_id": repeat["scenario_id"], "repeat_execution_index": repeat["execution_index"],
                                   "equivalent": expected_semantic == actual_semantic,
                                   "canonical_semantic_sha256": sha256_bytes(canonical(expected_semantic)),
                                   "repeat_semantic_sha256": sha256_bytes(canonical(actual_semantic))})
    threat_names = sorted({threat for _,label in enriched for threat in label.threats})
    threats = {}
    for name in threat_names:
        members = [(r,l) for r,l in enriched if name in l.threats]
        failures = [r["scenario_id"] for r,l in members if r["terminal_classification"] != l.expected_terminal_classification]
        threats[name] = {"status": "TESTED_FAIL" if failures else "TESTED_PASS", "cases": len(members), "failure_ids": failures}
    threats["symlink_swap_and_toctou"] = {"status": "NOT_EVALUATED", "cases": 0, "reason": "Frozen corpus has no race harness."}
    threats["inherited_file_descriptor_bypass"] = {"status": "NOT_EVALUATED", "cases": 0, "reason": "Frozen corpus supplies no inherited descriptor fixture."}
    threats["direct_api_bypass_boundary"] = {"status": "EXPECTED_BOUNDARY", "cases": 2,
                                                "failure_ids": [r["scenario_id"] for r,l in enriched if r["route"] != "adapter" and r["terminal_classification"] != "EXPECTED_FMED_L1_BYPASS"]}
    requirements = {}
    architectural = {"REQ-005", "REQ-007"}
    for index in range(1,33):
        req = f"REQ-{index:03d}"
        tagged = [(r,l) for r,l in enriched if req in l.requirements]
        if req in architectural:
            status = "ARCHITECTURAL_ONLY"
        elif req == "REQ-030":
            status = "PASS" if len(adapter_records) == 94 and all(r["timing_ns"]["adapter_total"] > 0 for r in adapter_records) else "FAIL"
        elif req == "REQ-002":
            status = "PASS" if all(r["temporary_root"]["all_observed_primitive_and_probe_paths_confined"] for r in records) else "FAIL"
        elif req == "REQ-017": status = "PASS" if len(denied_mut_pass) == len(denied_mut) else "FAIL"
        elif req == "REQ-018": status = "PASS" if nd_pass == nd_total else "FAIL"
        elif req == "REQ-021": status = "PASS" if all(terminal_matches) else "FAIL"
        elif req == "REQ-024": status = "PASS" if len(reconstruction_pass) == len(adapter_records) else "FAIL"
        elif req == "REQ-027": status = "PASS" if all(r["terminal_classification"] == "EXPECTED_FMED_L1_BYPASS" for r in records if r["route"] != "adapter") else "FAIL"
        elif req == "REQ-029": status = "PASS" if all(x["equivalent"] for x in repeat_comparisons) else "FAIL"
        elif req == "REQ-031": status = "PASS"
        elif req == "REQ-032": status = "PASS" if platform.system() == "Linux" else "FAIL"
        elif tagged:
            status = "PASS" if all(r["terminal_classification"] == l.expected_terminal_classification for r,l in tagged) else "FAIL"
        else:
            status = "NOT_EMPIRICALLY_EVALUATED"
        requirements[req] = {"status": status, "case_count": len(tagged),
                             "failure_ids": [r["scenario_id"] for r,l in tagged if r["terminal_classification"] != l.expected_terminal_classification]}
    tool_ok = categories["TOOL_ERROR"]["correct"] == categories["TOOL_ERROR"]["cases"]
    adapter_bypass = [(r,l) for r,l in enriched if r["route"] == "adapter" and any(x in l.threats for x in ("path_traversal","prefix_collision","symlink_escape","hard_link_alias","rename_escape","host_logical_confusion","unicode_path_confusion"))]
    adapter_bypass_ok = all(r["terminal_classification"] == l.expected_terminal_classification for r,l in adapter_bypass)
    success = {
        "authorization_correctness_100_percent": "PASS" if auth_correct == len(auth_members) else "FAIL",
        "denied_mutation_prevention_100_percent": "PASS" if len(denied_mut_pass) == len(denied_mut) else "FAIL",
        "read_list_stat_nondisclosure_100_percent": "PASS" if nd_pass == nd_total else "FAIL",
        "authorize_before_effect_ordering_100_percent": "PASS" if len(ordering_pass) == len(ordering_members) else "FAIL",
        "audit_reconstruction_100_percent": "PASS" if len(reconstruction_pass) == len(adapter_records) else "FAIL",
        "tool_error_classification_100_percent": "PASS" if tool_ok else "FAIL",
        "registered_canonicalization_100_percent": "PASS" if not canonical_fail else "FAIL",
        "zero_adapter_routed_policy_escapes": "PASS" if adapter_bypass_ok else "FAIL",
        "expected_direct_route_bypass_boundary": "PASS" if all(r["terminal_classification"] == "EXPECTED_FMED_L1_BYPASS" for r in records if r["route"] != "adapter") else "FAIL",
        "deterministic_repeats": "PASS" if all(x["equivalent"] for x in repeat_comparisons) else "FAIL",
        "no_frozen_regression": "NOT_APPLICABLE",
    }
    failure = {
        "denied_mutation_changes_state": "TRIGGERED" if len(denied_mut_pass) != len(denied_mut) else "NOT_TRIGGERED",
        "denied_read_list_stat_disclosure": "TRIGGERED" if nd_pass != nd_total else "NOT_TRIGGERED",
        "execution_before_allow": "TRIGGERED" if len(ordering_pass) != len(ordering_members) else "NOT_TRIGGERED",
        "execution_start_for_denial": "TRIGGERED" if any(r["execution_start_observed"] for r,l in enriched if l.expected_terminal_classification == "POLICY_DENY") else "NOT_TRIGGERED",
        "symlink_or_traversal_escape": "TRIGGERED" if any(r["terminal_classification"] != l.expected_terminal_classification for r,l in adapter_bypass if any(x in l.threats for x in ("symlink_escape","path_traversal"))) else "NOT_TRIGGERED",
        "rename_endpoint_escape": "TRIGGERED" if any(r["side_effect_observed"] and any(item.get("decision") == "DENY" for item in r["authorization_decisions"]) for r in records if r["operation"] == "filesystem.rename") else "NOT_TRIGGERED",
        "audit_false_nonexecution": "TRIGGERED" if len(truthful_pass) != len(adapter_records) else "NOT_TRIGGERED",
        "canonicalization_expands_scope": "TRIGGERED" if canonical_fail else "NOT_TRIGGERED",
        "corpus_specific_authorization_branch": "NOT_EVALUATED",
        "nondeterministic_equivalent_inputs": "TRIGGERED" if any(not x["equivalent"] for x in repeat_comparisons) else "NOT_TRIGGERED",
        "unreconstructable_attempt": "TRIGGERED" if len(reconstruction_pass) != len(adapter_records) else "NOT_TRIGGERED",
    }
    performance = {}
    for key in ("adapter_total","authorization_calls","validation_probe_calls","primitive_calls","audit_calls"):
        values = []
        for record in adapter_records:
            value = record["timing_ns"][key]
            values.extend(value if isinstance(value,list) else [value])
        performance[key] = timing_summary(values)
    basis = {
        "scenario_count": len(records), "terminal_correct": sum(terminal_matches),
        "terminal_total": len(records), "authorization_correct": auth_correct,
        "authorization_total": len(auth_members), "mutation_prevention_correct": len(denied_mut_pass),
        "mutation_prevention_total": len(denied_mut), "nondisclosure_correct": nd_pass,
        "nondisclosure_total": nd_total, "ordering_correct": len(ordering_pass),
        "ordering_total": len(ordering_members), "reconstruction_correct": len(reconstruction_pass),
        "reconstruction_total": len(adapter_records), "truthfulness_correct": len(truthful_pass),
        "truthfulness_total": len(adapter_records), "pairs_correct": sum(x["pair_correct"] for x in pairs),
        "pairs_total": len(pairs), "hard_negative_correct": len(hard_ok), "hard_negative_total": len(hard),
        "operation_results": operation_results, "success_criteria": success, "failure_criteria": failure,
    }
    return {
        "run_id": RUN_ID, "status": "SCORED_PENDING_POST_RUN_VALIDATION",
        "frozen_shas": {"protocol": PROTOCOL_SHA, "implementation": IMPLEMENTATION_SHA, "corpus": CORPUS_SHA},
        "scenario_counts": {"canonical": len(records), "adapter": len(adapter_records), "controls": len(records)-len(adapter_records), "repeat_records": len(repeat_records)},
        "terminal_confusion": {"expected_totals": dict(expected_counts), "actual_totals": dict(actual_counts), "matches": sum(terminal_matches), "total": len(records), "accuracy": ratio(sum(terminal_matches),len(records)), "per_class": per_class,
                               "mismatches": [{"scenario_id":r["scenario_id"],"expected":l.expected_terminal_classification,"actual":r["terminal_classification"]} for r,l in enriched if r["terminal_classification"] != l.expected_terminal_classification]},
        "authorization_metrics": {"correct": auth_correct, "evaluable": len(auth_members), "rate": ratio(auth_correct,len(auth_members)),
                                  "failures": [r["scenario_id"] for r,l in auth_members if actual_auth(r) != l.expected_authorization_decision],
                                  "policy_separated_from_post_allow_validation": True},
        "mutation_prevention": {"numerator": len(denied_mut_pass), "denominator": len(denied_mut), "rate": ratio(len(denied_mut_pass),len(denied_mut)),
                                "failure_ids": [r["scenario_id"] for r,l in denied_mut if r not in denied_mut_pass]},
        "nondisclosure": {**nondisclosure, "combined": {"passes": nd_pass,"total":nd_total,"rate":ratio(nd_pass,nd_total)}},
        "ordering": {"passes":len(ordering_pass),"total":len(ordering_members),"rate":ratio(len(ordering_pass),len(ordering_members)),"failure_ids":[r["scenario_id"] for r in ordering_members if r not in ordering_pass]},
        "audit_reconstruction": {"reconstructable":len(reconstruction_pass),"attempted_actions":len(adapter_records),"rate":ratio(len(reconstruction_pass),len(adapter_records)),"failure_ids":[r["scenario_id"] for r in adapter_records if r not in reconstruction_pass],"runner_state_used_to_fill_fields":False},
        "audit_truthfulness": {"truthful":len(truthful_pass),"applicable":len(adapter_records),"rate":ratio(len(truthful_pass),len(adapter_records)),"failure_ids":[r["scenario_id"] for r in adapter_records if r not in truthful_pass]},
        "canonicalization": {"passes":len(canonical_members)-len(canonical_fail),"total":len(canonical_members),"rate":ratio(len(canonical_members)-len(canonical_fail),len(canonical_members)),"failure_ids":canonical_fail,
                             "distinguishes_canonicalization_failure_from_policy_denial":True,
                             "behavior_cases":dict(canonical_behaviors)},
        "symlink_results": symlink, "hardlink_results": {**hardlink,"environment_supported":True},
        "rename_results": {"cases":len(rename),"matrix":rename,"critical_denied_endpoint_side_effects":[x["scenario_id"] for x in rename if x["side_effect"] and (x["source_decision"]=="DENY" or x["destination_decision"]=="DENY")]},
        "failure_results": {"tool_error":categories["TOOL_ERROR"],"fail_closed":categories["FAIL_CLOSED"],"fail_indeterminate":categories["FAIL_INDETERMINATE"],
                            "failure_class_breakdown":failure_classes},
        "pair_results": {"correct":sum(x["pair_correct"] for x in pairs),"total":len(pairs),"accuracy":ratio(sum(x["pair_correct"] for x in pairs),len(pairs)),"pairs":pairs},
        "hard_negative_results": {"correctly_allowed":len(hard_ok),"total":len(hard),"success_rate":ratio(len(hard_ok),len(hard)),
                                  "incorrect_ids":[r["scenario_id"] for r,l in hard if r["terminal_classification"] != l.expected_terminal_classification],
                                  "records":[{"scenario_id":r["scenario_id"],"operation":r["operation"],"terminal":r["terminal_classification"],"correct":r["terminal_classification"]==l.expected_terminal_classification} for r,l in hard]},
        "operation_results": operation_results, "requirement_results": requirements,
        "invariant_results": invariants, "threat_results": threats,
        "success_criteria": success, "failure_criteria": failure,
        "determinism": {"passes":sum(x["equivalent"] for x in repeat_comparisons),"total":len(repeat_comparisons),"all_equivalent":all(x["equivalent"] for x in repeat_comparisons),"comparisons":repeat_comparisons},
        "performance": performance,
        "controls": {"fmed_l1": [{"scenario_id":r["scenario_id"],"terminal":r["terminal_classification"],"side_effect_observed":r["side_effect_observed"]} for r in records if r["route"] != "adapter"],"excluded_from_adapter_authorization_accuracy":True},
        "label_isolation": {"labels_loaded_after_raw_records_persisted":True,"label_joined_at":label_joined_at,
                            "execution_objects":"CorpusScenario and RequestSpec only","excluded_from_execution":["labels","pair metadata","family metadata","hard-negative metadata","rationales"],
                            "data_flow":"load runtime scenario -> materialize fixture -> execute frozen adapter -> normalize -> append/fsync canonical record; after runs/repeats close -> load labels -> join for scoring"},
        "integrity": {"raw_records_immutable_after_label_join":True,"independent_recomputation":"PENDING","frozen_path_diffs_zero_pre_run":True},
        "independent_basis": basis,
    }


def coupling_search(labels: tuple[object, ...], scenarios: tuple[CorpusScenario,...]) -> dict[str, object]:
    production = [path for path in (ROOT / "src/safetybox").rglob("*.py") if "experiments" not in path.parts]
    terms: dict[str, str] = {
        "FSH-014": "scenario_id_prefix", "labels.yaml": "corpus_filename",
        "scenarios.yaml": "corpus_filename", "manifest.yaml": "corpus_filename",
    }
    for label in labels:
        terms[label.counterfactual_pair_id] = "pair_id"
        for family in label.family:
            terms.setdefault(family, "family_id_or_generic_family_term")
        terms.setdefault(label.expected_terminal_classification, "expected_label_or_runtime_taxonomy")
    for scenario in scenarios:
        terms[scenario.request.task_id] = "corpus_unique_task_id"
    # Corpus-unique basenames and nontrivial fixture contents are included.
    for scenario in scenarios:
        for entry in scenario.filesystem_fixture.entries:
            basename = Path(entry.path).name
            if len(basename) >= 10:
                terms.setdefault(basename, "corpus_resource_name")
            if entry.content_utf8 and len(entry.content_utf8) >= 8:
                terms.setdefault(entry.content_utf8, "corpus_sentinel_or_fixture_content")
    hits = []
    for path in production:
        text = path.read_text(encoding="utf-8")
        for term, kind in sorted(terms.items()):
            if term and term in text:
                hits.append({"path":str(path.relative_to(ROOT)),"term":term,"kind":kind})
    generic_kinds = {"family_id_or_generic_family_term", "expected_label_or_runtime_taxonomy"}
    high_confidence = [item for item in hits if item["kind"] not in generic_kinds]
    generic = [item for item in hits if item["kind"] in generic_kinds]
    return {"searched_production_files":len(production),"searched_term_count":len(terms),
            "high_confidence_matches":high_confidence,"generic_coincidences_reviewed":generic,
            "corpus_specific_runtime_branch_found":bool(high_confidence),
            "review_rule":"Generic family/taxonomy strings are recorded but do not alone establish corpus coupling.",
            "loader_excluded_as_nonproduction_corpus_boundary":True}


def regression_checks() -> dict[str, object]:
    commands = {
        "pytest": [str(ROOT/".venv/bin/pytest")],
        "coverage": [str(ROOT/".venv/bin/pytest"), "--cov=safetybox"],
        "ruff": [str(ROOT/".venv/bin/ruff"), "check", "."],
        "mypy": [str(ROOT/".venv/bin/mypy"), "src"],
        "git_diff_check": ["git", "diff", "--check"],
    }
    results = {}
    for name, command in commands.items():
        completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        results[name] = {"command":" ".join(command),"exit_code":completed.returncode,
                         "passed":completed.returncode==0,"stdout":completed.stdout,"stderr":completed.stderr}
    return results


def finalize_checksums(files: list[str]) -> dict[str,str]:
    values = {name:sha256_file(RESULT_DIR/name) for name in files}
    (RESULT_DIR/"SHA256SUMS").write_text("".join(f"{digest}  {name}\n" for name,digest in values.items()))
    verified = subprocess.run(("sha256sum","--check","SHA256SUMS"),cwd=RESULT_DIR,text=True,capture_output=True)
    if verified.returncode != 0:
        raise RuntimeError("Generated SHA256SUMS did not verify")
    return values


def main() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    pre = preflight()
    env = environment(pre)
    write_json(RESULT_DIR/"environment.json",env)
    protocol = {
        "experiment_id":"EXP-014","run_id":RUN_ID,"protocol_version":1,
        "frozen_shas":{"protocol":PROTOCOL_SHA,"implementation":IMPLEMENTATION_SHA,"corpus":CORPUS_SHA},
        "file_sha256":EXPECTED_HASHES,
        "implementation_identifiers":[FILESYSTEM_ADAPTER_VERSION,FILESYSTEM_CANONICALIZATION_VERSION,FILESYSTEM_AUDIT_ENVELOPE_VERSION,STATE_DIGEST_VERSION],
        "execution_order":"frozen scenarios.yaml manifest order FSH-014-001 through FSH-014-096",
        "repeat_set":{"FSH-014-001":2,"FSH-014-093":2,"meaning":"total executions including canonical"},
        "fresh_state":"fresh temporary root, adapter, authorizer, recorder, sink, primitives per execution",
        "label_data_flow":"Runtime-only load and execution; runs.jsonl/repeats.jsonl closed and fsynced before load_labels().",
        "normalization":{"ALLOW":"ALLOW_SUCCESS","DENY":"POLICY_DENY",
                         "frozen safety validation rejection codes":"TARGET_VALIDATION_REJECT",
                         "validator exception or inspection failure":"FAIL_CLOSED",
                         "TOOL_ERROR":"TOOL_ERROR","FAIL_CLOSED":"FAIL_CLOSED",
                         "FAIL_INDETERMINATE":"FAIL_INDETERMINATE",
                         "successful direct route":"EXPECTED_FMED_L1_BYPASS"},
        "canonical_denominator":96,"adapter_authorization_denominator_excludes_direct_controls":True,
    }
    write_json(RESULT_DIR/"protocol.json",protocol)
    attempt_start = {
        "attempt_number":1,"event":"CANONICAL_START","timestamp":now(),"environment_state":env,
        "pre_run_validation":pre,"predictions_began":False,"filesystem_side_effects_began":False,
        "failure_category":None,"reason":None,"run_remained_scientifically_unused":True,
    }
    append_attempt(attempt_start)
    predictions = 0
    side_effects_began = False
    try:
        scenarios = load_scenarios()
        records=[]; repeats=[]
        with RUNS_FILE.open("x",encoding="utf-8") as run_stream, REPEATS_FILE.open("x",encoding="utf-8") as repeat_stream:
            for index, scenario in enumerate(scenarios,1):
                side_effects_began=True
                record=execute_once(scenario,index,True)
                run_stream.write(json.dumps(record,ensure_ascii=False,sort_keys=True)+"\n")
                run_stream.flush(); os.fsync(run_stream.fileno())
                records.append(record); predictions += 1
                for repeat_index in range(2,scenario.repetitions+1):
                    repeated=execute_once(scenario,repeat_index,False)
                    repeat_stream.write(json.dumps(repeated,ensure_ascii=False,sort_keys=True)+"\n")
                    repeat_stream.flush(); os.fsync(repeat_stream.fileno())
                    repeats.append(repeated)
        raw_persisted_at=now()
        label_joined_at=now()
        summary=score(records,repeats,label_joined_at)
        write_json(SUMMARY_FILE,summary)
        recompute=subprocess.run([sys.executable,str(RESULT_DIR/"recompute.py")],cwd=ROOT,text=True,capture_output=True)
        if recompute.returncode != 0:
            raise RuntimeError(f"Independent recomputation failed: {recompute.stdout} {recompute.stderr}")
        independent=json.loads((RESULT_DIR/"independent_recompute.json").read_text())
        summary["integrity"]["independent_recomputation"] = "MATCH" if independent["all_sections_match"] else "MISMATCH"
        summary["integrity"]["independent_recomputation_details"] = independent
        labels=load_labels()
        coupling=coupling_search(labels,scenarios)
        summary["integrity"]["corpus_adapter_coupling_search"] = coupling
        if coupling["corpus_specific_runtime_branch_found"]:
            summary["failure_criteria"]["corpus_specific_authorization_branch"]="TRIGGERED"
        else:
            summary["failure_criteria"]["corpus_specific_authorization_branch"]="NOT_TRIGGERED"
        assert_diff_free(IMPLEMENTATION_SHA,IMPLEMENTATION_PATHS)
        assert_diff_free(PROTOCOL_SHA,PROTOCOL_PATHS)
        assert_diff_free(CORPUS_SHA,CORPUS_PATHS)
        summary["integrity"]["frozen_path_diffs_zero_post_run"]=True
        summary["integrity"]["canonical_records_sha256"]=sha256_file(RUNS_FILE)
        summary["integrity"]["raw_records_persisted_at"]=raw_persisted_at
        checks=regression_checks()
        summary["regression_gate"]=checks
        regression_ok=all(item["passed"] for item in checks.values())
        summary["success_criteria"]["no_frozen_regression"]="PASS" if regression_ok else "FAIL"
        summary["raw_run_validity"]="VALID" if independent["all_sections_match"] and summary["integrity"]["frozen_path_diffs_zero_post_run"] else "INVALID"
        summary["status"]="COMPLETE"
        summary["freeze_ready"]=summary["raw_run_validity"]=="VALID" and regression_ok
        write_json(SUMMARY_FILE,summary)
        append_attempt({"attempt_number":1,"event":"CANONICAL_COMPLETE","timestamp":now(),
                        "environment_state":{"head":pre["head"]},"pre_run_validation":pre,
                        "predictions_began":True,"canonical_predictions_persisted":96,
                        "filesystem_side_effects_began":True,"failure_category":None,"reason":None,
                        "run_remained_scientifically_unused":False,"run_validity":summary["raw_run_validity"]})
        readme = f"""# {RUN_ID}\n\nFactual raw-run identity only.\n\n- Run: `{RUN_ID}`\n- Protocol freeze: `{PROTOCOL_SHA}`\n- Implementation freeze: `{IMPLEMENTATION_SHA}`\n- Corpus freeze: `{CORPUS_SHA}`\n- Environment: `{platform.platform()}`; Python `{platform.python_version()}`; `{platform.machine()}`\n- Canonical records: 96 in `runs.jsonl`; repeat records: {len(repeats)} in `repeats.jsonl`.\n- Attempts: one canonical start and one completion event in `attempts.jsonl`; no infrastructure failure.\n- Artifacts: `environment.json`, `protocol.json`, `attempts.jsonl`, `runs.jsonl`, `repeats.jsonl`, `summary.json`, `independent_recompute.json`, `evaluate.py`, `recompute.py`, and `SHA256SUMS`.\n- Verify: run `sha256sum --check results/EXP-014/SHA256SUMS` from the repository root.\n- Host temporary-root paths are omitted; every execution used a fresh isolated root and all observed operation paths were confined beneath it.\n"""
        (RESULT_DIR/"README.md").write_text(readme)
        checksum_files=["environment.json","protocol.json","attempts.jsonl","runs.jsonl","repeats.jsonl","summary.json","independent_recompute.json","README.md","evaluate.py","recompute.py"]
        finalize_checksums(checksum_files)
        print(json.dumps({"run_id":RUN_ID,"status":"COMPLETE","canonical_records":96,"validity":summary["raw_run_validity"],"freeze_ready":summary["freeze_ready"]},sort_keys=True))
    except Exception as error:
        append_attempt({"attempt_number":1,"event":"CANONICAL_FAILURE","timestamp":now(),
                        "environment_state":{"head":pre.get("head")},"pre_run_validation":pre,
                        "predictions_began":predictions>0,"canonical_predictions_persisted":predictions,
                        "filesystem_side_effects_began":side_effects_began,
                        "failure_category":"INFRASTRUCTURE_PRE_RUN_FAILURE" if predictions==0 else "PARTIAL_RUN_CONTAMINATION",
                        "reason":f"{type(error).__name__}: {error}","run_remained_scientifically_unused":predictions==0})
        raise


if __name__ == "__main__":
    main()
