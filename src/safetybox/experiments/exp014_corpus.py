"""Typed, detector-independent loader for EXP-014-CORPUS@1.

The module validates frozen corpus data only.  It deliberately imports no filesystem
adapter, canonicalizer, validator, primitive, monitor, or policy implementation and has
no execution method.  Ground-truth labels are loaded through a separate API.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Literal, cast

Operation = Literal[
    "filesystem.read",
    "filesystem.write",
    "filesystem.append",
    "filesystem.create",
    "filesystem.delete",
    "filesystem.rename",
    "filesystem.mkdir",
    "filesystem.list",
    "filesystem.stat",
]
Route = Literal["adapter", "direct_os_open", "direct_pathlib_write"]
FixtureType = Literal["directory", "file", "symlink", "hard_link"]

OPERATIONS: frozenset[str] = frozenset(
    {
        "filesystem.read",
        "filesystem.write",
        "filesystem.append",
        "filesystem.create",
        "filesystem.delete",
        "filesystem.rename",
        "filesystem.mkdir",
        "filesystem.list",
        "filesystem.stat",
    }
)
ROUTES: frozenset[str] = frozenset({"adapter", "direct_os_open", "direct_pathlib_write"})
FIXTURE_TYPES: frozenset[str] = frozenset({"directory", "file", "symlink", "hard_link"})
INJECTION_TYPES: frozenset[str] = frozenset(
    {
        "permission_error_before_effect",
        "authorization_exception",
        "validator_exception_before_effect",
        "reject_execution_started",
        "partial_write_then_error",
        "reject_terminal_success",
    }
)
RESULT_CATEGORIES: frozenset[str] = frozenset(
    {"ALLOW", "DENY", "FAIL_CLOSED", "TOOL_ERROR", "FAIL_INDETERMINATE"}
)
TERMINAL_CLASSIFICATIONS: frozenset[str] = frozenset(
    {
        "ALLOW_SUCCESS",
        "POLICY_DENY",
        "TARGET_VALIDATION_REJECT",
        "TOOL_ERROR",
        "FAIL_CLOSED",
        "FAIL_INDETERMINATE",
        "EXPECTED_FMED_L1_BYPASS",
    }
)


class CorpusValidationError(ValueError):
    """Raised when frozen corpus data violates its authoring schema."""


@dataclass(frozen=True, slots=True)
class CapabilitySpec:
    action: Operation
    resource: str


@dataclass(frozen=True, slots=True)
class TaskContractSpec:
    task_id: str
    description: str
    capabilities: tuple[CapabilitySpec, ...]


@dataclass(frozen=True, slots=True)
class FixtureEntry:
    type: FixtureType
    path: str
    content_utf8: str | None = None
    content_hex: str | None = None
    target: str | None = None
    target_kind: str | None = None
    source: str | None = None


@dataclass(frozen=True, slots=True)
class FilesystemFixture:
    entries: tuple[FixtureEntry, ...]

    @property
    def sha256(self) -> str:
        """Return a deterministic hash of the declarative fixture description."""

        payload = [
            {
                key: value
                for key, value in (
                    ("type", entry.type),
                    ("path", entry.path),
                    ("content_utf8", entry.content_utf8),
                    ("content_hex", entry.content_hex),
                    ("target", entry.target),
                    ("target_kind", entry.target_kind),
                    ("source", entry.source),
                )
                if value is not None
            }
            for entry in self.entries
        ]
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class RequestSpec:
    session_id: str
    task_id: str
    request_id: str
    actor: str
    operation: Operation
    resource: str
    destination: str | None = None
    data_utf8: str | None = None
    data_hex: str | None = None

    def adapter_payload(self) -> dict[str, object]:
        """Return only runtime request fields; no labels or author metadata can enter."""

        value: dict[str, object] = {
            "session_id": self.session_id,
            "task_id": self.task_id,
            "request_id": self.request_id,
            "actor": self.actor,
            "operation": self.operation,
            "resource": self.resource,
        }
        if self.destination is not None:
            value["destination"] = self.destination
        if self.data_utf8 is not None:
            value["data"] = self.data_utf8.encode("utf-8")
        if self.data_hex is not None:
            value["data"] = bytes.fromhex(self.data_hex)
        return value


@dataclass(frozen=True, slots=True)
class DependencyInjectionSpec:
    boundary: str
    type: str
    partial_bytes: int | None = None


@dataclass(frozen=True, slots=True)
class CorpusScenario:
    """One primary scenario/session evaluation unit without ground truth."""

    scenario_id: str
    version: int
    route: Route
    task_contract: TaskContractSpec
    filesystem_fixture: FilesystemFixture
    request: RequestSpec
    dependency_injection: DependencyInjectionSpec | None
    environment_requirements: tuple[str, ...]
    repetitions: int


@dataclass(frozen=True, slots=True)
class CorpusLabel:
    """Author-only/scoring metadata, never part of ``CorpusScenario``."""

    scenario_id: str
    version: int
    expected_terminal_classification: str
    expected_result_category: str | None
    expected_authorization_decision: str | None
    expected_physical_validation: str | None
    authorization_metric_member: bool
    adapter_correctness_denominator: bool
    family: tuple[str, ...]
    counterfactual_pair_id: str
    pair_role: str
    pair_strength: str
    semantic_variable: str
    hard_negative: bool
    requirements: tuple[str, ...]
    invariants: tuple[str, ...]
    threats: tuple[str, ...]
    success_criteria: tuple[str, ...]
    failure_criteria: tuple[str, ...]
    rationale: str


def corpus_directory() -> Path:
    return Path(__file__).resolve().parents[3] / "experiments" / "EXP-014" / "corpus"


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CorpusValidationError(f"duplicate JSON/YAML key: {key}")
        result[key] = value
    return result


def _load_document(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (OSError, json.JSONDecodeError) as error:
        raise CorpusValidationError(f"cannot load {path}: {error}") from error
    if not isinstance(value, dict):
        raise CorpusValidationError(f"{path} must contain one object")
    return value


def _expect_keys(value: dict[str, Any], expected: set[str], where: str) -> None:
    actual = set(value)
    if actual != expected:
        raise CorpusValidationError(
            f"{where} keys differ: missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )


def _canonical_fixture_path(value: object, where: str) -> str:
    if not isinstance(value, str) or "\x00" in value or not value.startswith("/workspace/"):
        raise CorpusValidationError(f"{where} must be a /workspace descendant")
    path = PurePosixPath(value)
    if str(path) != value or any(part in {"", ".", ".."} for part in path.parts[1:]):
        raise CorpusValidationError(f"{where} must be canonical POSIX form")
    return value


def _request_path(value: object, where: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise CorpusValidationError(f"{where} must be a nonempty NUL-free POSIX string")
    return value


def _operation(value: object, where: str) -> Operation:
    if value not in OPERATIONS:
        raise CorpusValidationError(f"{where} has unknown operation {value!r}")
    return cast(Operation, value)


def _capability(raw: object, where: str) -> CapabilitySpec:
    if not isinstance(raw, dict):
        raise CorpusValidationError(f"{where} must be an object")
    _expect_keys(raw, {"action", "resource"}, where)
    action = _operation(raw["action"], f"{where}.action")
    resource = raw["resource"]
    if not isinstance(resource, str) or not (
        resource == "/workspace" or resource.startswith("/workspace/")
    ):
        raise CorpusValidationError(f"{where}.resource must be a logical absolute scope")
    root = resource.removesuffix("/**")
    if root != "/workspace":
        _canonical_fixture_path(root, f"{where}.resource")
    return CapabilitySpec(action, resource)


def _fixture_entry(raw: object, where: str, earlier_paths: set[str]) -> FixtureEntry:
    if not isinstance(raw, dict):
        raise CorpusValidationError(f"{where} must be an object")
    allowed = {"type", "path", "content_utf8", "content_hex", "target", "target_kind", "source"}
    if set(raw) - allowed or not {"type", "path"} <= set(raw):
        raise CorpusValidationError(f"{where} has missing or unknown fields")
    entry_type = raw["type"]
    if entry_type not in FIXTURE_TYPES:
        raise CorpusValidationError(f"{where}.type is unknown")
    path = _canonical_fixture_path(raw["path"], f"{where}.path")
    if path in earlier_paths:
        raise CorpusValidationError(f"{where}.path duplicates {path}")
    content_utf8 = raw.get("content_utf8")
    content_hex = raw.get("content_hex")
    target = raw.get("target")
    target_kind = raw.get("target_kind")
    source = raw.get("source")
    if entry_type == "file":
        if (content_utf8 is None) == (content_hex is None):
            raise CorpusValidationError(f"{where} file needs exactly one content encoding")
        if content_utf8 is not None and not isinstance(content_utf8, str):
            raise CorpusValidationError(f"{where}.content_utf8 must be a string")
        if content_hex is not None:
            if not isinstance(content_hex, str):
                raise CorpusValidationError(f"{where}.content_hex must be a string")
            try:
                bytes.fromhex(content_hex)
            except ValueError as error:
                raise CorpusValidationError(f"{where}.content_hex is invalid") from error
    elif content_utf8 is not None or content_hex is not None:
        raise CorpusValidationError(f"{where} non-file entry cannot carry content")
    if entry_type == "symlink":
        if not isinstance(target, str) or target_kind not in {"relative", "logical_absolute"}:
            raise CorpusValidationError(f"{where} symlink target is incomplete")
        if target_kind == "logical_absolute":
            _canonical_fixture_path(target, f"{where}.target")
        elif target.startswith("/") or "\x00" in target:
            raise CorpusValidationError(f"{where} relative symlink target is invalid")
    elif target is not None or target_kind is not None:
        raise CorpusValidationError(f"{where} non-symlink entry cannot carry target")
    if entry_type == "hard_link":
        source = _canonical_fixture_path(source, f"{where}.source")
        if source not in earlier_paths:
            raise CorpusValidationError(f"{where}.source must name an earlier fixture entry")
    elif source is not None:
        raise CorpusValidationError(f"{where} non-hard-link entry cannot carry source")
    return FixtureEntry(
        cast(FixtureType, entry_type), path, content_utf8, content_hex, target, target_kind, source
    )


def _scenario(raw: object, index: int) -> CorpusScenario:
    where = f"scenarios[{index}]"
    if not isinstance(raw, dict):
        raise CorpusValidationError(f"{where} must be an object")
    _expect_keys(
        raw,
        {
            "scenario_id",
            "version",
            "route",
            "task_contract",
            "filesystem_fixture",
            "request",
            "dependency_injection",
            "environment_requirements",
            "repetitions",
        },
        where,
    )
    scenario_id = raw["scenario_id"]
    if not isinstance(scenario_id, str) or not scenario_id.startswith("FSH-014-"):
        raise CorpusValidationError(f"{where}.scenario_id is invalid")
    if raw["version"] != 1:
        raise CorpusValidationError(f"{where}.version must be 1")
    route = raw["route"]
    if route not in ROUTES:
        raise CorpusValidationError(f"{where}.route is unknown")

    contract = raw["task_contract"]
    if not isinstance(contract, dict):
        raise CorpusValidationError(f"{where}.task_contract must be an object")
    _expect_keys(contract, {"task_id", "description", "capabilities"}, f"{where}.task_contract")
    if not isinstance(contract["task_id"], str) or not contract["task_id"]:
        raise CorpusValidationError(f"{where}.task_contract.task_id is invalid")
    if not isinstance(contract["description"], str) or not contract["description"]:
        raise CorpusValidationError(f"{where}.task_contract.description is invalid")
    raw_capabilities = contract["capabilities"]
    if not isinstance(raw_capabilities, list):
        raise CorpusValidationError(f"{where}.task_contract.capabilities must be a list")
    capabilities = tuple(
        _capability(item, f"{where}.task_contract.capabilities[{cap_index}]")
        for cap_index, item in enumerate(raw_capabilities)
    )
    if len(set(capabilities)) != len(capabilities):
        raise CorpusValidationError(f"{where} has duplicate capabilities")
    task_contract = TaskContractSpec(
        contract["task_id"], contract["description"], capabilities
    )

    fixture = raw["filesystem_fixture"]
    if not isinstance(fixture, dict):
        raise CorpusValidationError(f"{where}.filesystem_fixture must be an object")
    _expect_keys(fixture, {"entries"}, f"{where}.filesystem_fixture")
    if not isinstance(fixture["entries"], list):
        raise CorpusValidationError(f"{where}.filesystem_fixture.entries must be a list")
    paths: set[str] = set()
    entries: list[FixtureEntry] = []
    for fixture_index, item in enumerate(fixture["entries"]):
        entry = _fixture_entry(item, f"{where}.filesystem_fixture.entries[{fixture_index}]", paths)
        paths.add(entry.path)
        entries.append(entry)

    request = raw["request"]
    if not isinstance(request, dict):
        raise CorpusValidationError(f"{where}.request must be an object")
    required_request = {"session_id", "task_id", "request_id", "actor", "operation", "resource"}
    allowed_request = required_request | {"destination", "data_utf8", "data_hex"}
    if not required_request <= set(request) or set(request) - allowed_request:
        raise CorpusValidationError(f"{where}.request has missing or unknown fields")
    for key in ("session_id", "task_id", "request_id", "actor"):
        if not isinstance(request[key], str) or not request[key]:
            raise CorpusValidationError(f"{where}.request.{key} is invalid")
    operation = _operation(request["operation"], f"{where}.request.operation")
    resource = _request_path(request["resource"], f"{where}.request.resource")
    destination = request.get("destination")
    data_utf8 = request.get("data_utf8")
    data_hex = request.get("data_hex")
    if operation == "filesystem.rename":
        destination = _request_path(destination, f"{where}.request.destination")
    elif destination is not None:
        raise CorpusValidationError(f"{where} only rename accepts destination")
    if operation in {"filesystem.write", "filesystem.append", "filesystem.create"}:
        if (data_utf8 is None) == (data_hex is None):
            raise CorpusValidationError(f"{where} data operation needs one encoding")
        if data_utf8 is not None and not isinstance(data_utf8, str):
            raise CorpusValidationError(f"{where}.request.data_utf8 must be a string")
        if data_hex is not None:
            if not isinstance(data_hex, str):
                raise CorpusValidationError(f"{where}.request.data_hex must be a string")
            try:
                bytes.fromhex(data_hex)
            except ValueError as error:
                raise CorpusValidationError(f"{where}.request.data_hex is invalid") from error
    elif data_utf8 is not None or data_hex is not None:
        raise CorpusValidationError(f"{where} non-data operation cannot carry bytes")
    request_spec = RequestSpec(
        request["session_id"],
        request["task_id"],
        request["request_id"],
        request["actor"],
        operation,
        resource,
        destination,
        data_utf8,
        data_hex,
    )

    injection_raw = raw["dependency_injection"]
    injection = None
    if injection_raw is not None:
        if not isinstance(injection_raw, dict):
            raise CorpusValidationError(f"{where}.dependency_injection must be an object or null")
        required_injection = {"boundary", "type"}
        if not required_injection <= set(injection_raw) or set(injection_raw) - {
            "boundary",
            "type",
            "partial_bytes",
        }:
            raise CorpusValidationError(f"{where}.dependency_injection has invalid fields")
        if injection_raw["type"] not in INJECTION_TYPES:
            raise CorpusValidationError(f"{where} has unknown failure injection")
        partial_bytes = injection_raw.get("partial_bytes")
        if partial_bytes is not None and (not isinstance(partial_bytes, int) or partial_bytes <= 0):
            raise CorpusValidationError(f"{where}.partial_bytes must be positive")
        injection = DependencyInjectionSpec(
            injection_raw["boundary"], injection_raw["type"], partial_bytes
        )

    environment = raw["environment_requirements"]
    if not isinstance(environment, list) or not environment or not all(
        isinstance(item, str) and item for item in environment
    ):
        raise CorpusValidationError(f"{where}.environment_requirements is invalid")
    repetitions = raw["repetitions"]
    if not isinstance(repetitions, int) or repetitions < 1:
        raise CorpusValidationError(f"{where}.repetitions must be positive")
    return CorpusScenario(
        scenario_id,
        1,
        cast(Route, route),
        task_contract,
        FilesystemFixture(tuple(entries)),
        request_spec,
        injection,
        tuple(environment),
        repetitions,
    )


def load_scenarios(path: Path | None = None) -> tuple[CorpusScenario, ...]:
    """Load and validate runtime-only scenarios without opening the labels file."""

    document = _load_document(path or corpus_directory() / "scenarios.yaml")
    _expect_keys(
        document,
        {"corpus_id", "version", "status", "schema_version", "scenarios"},
        "root",
    )
    if document["corpus_id"] != "EXP-014-CORPUS@1" or document["version"] != 1:
        raise CorpusValidationError("scenario corpus identity/version mismatch")
    if document["status"] != "READY_FOR_FREEZE":
        raise CorpusValidationError("scenario corpus status mismatch")
    if document["schema_version"] != "EXP-014-CORPUS-SCENARIO@1":
        raise CorpusValidationError("scenario schema version mismatch")
    raw_scenarios = document["scenarios"]
    if not isinstance(raw_scenarios, list):
        raise CorpusValidationError("scenarios must be a list")
    scenarios = tuple(_scenario(raw, index) for index, raw in enumerate(raw_scenarios))
    ids = [item.scenario_id for item in scenarios]
    request_ids = [item.request.request_id for item in scenarios]
    if len(ids) != len(set(ids)):
        raise CorpusValidationError("scenario IDs are not unique")
    if len(request_ids) != len(set(request_ids)):
        raise CorpusValidationError("request IDs are not unique")
    return scenarios


def _string_tuple(raw: dict[str, Any], key: str, where: str) -> tuple[str, ...]:
    value = raw[key]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise CorpusValidationError(f"{where}.{key} must be a string list")
    return tuple(value)


def load_labels(path: Path | None = None) -> tuple[CorpusLabel, ...]:
    """Load scoring metadata separately; evaluation must join only after execution."""

    document = _load_document(path or corpus_directory() / "labels.yaml")
    _expect_keys(document, {"corpus_id", "version", "status", "taxonomy", "entries"}, "labels")
    if document["corpus_id"] != "EXP-014-CORPUS@1" or document["version"] != 1:
        raise CorpusValidationError("label corpus identity/version mismatch")
    taxonomy = document["taxonomy"]
    if not isinstance(taxonomy, dict):
        raise CorpusValidationError("taxonomy must be an object")
    _expect_keys(taxonomy, {"frozen_result_categories", "terminal_classifications"}, "taxonomy")
    if set(taxonomy["frozen_result_categories"]) != RESULT_CATEGORIES:
        raise CorpusValidationError("frozen result taxonomy mismatch")
    if set(taxonomy["terminal_classifications"]) != TERMINAL_CLASSIFICATIONS:
        raise CorpusValidationError("terminal classification taxonomy mismatch")
    raw_entries = document["entries"]
    if not isinstance(raw_entries, list):
        raise CorpusValidationError("label entries must be a list")
    expected_keys = {
        "scenario_id",
        "version",
        "expected_terminal_classification",
        "expected_result_category",
        "expected_authorization_decision",
        "expected_physical_validation",
        "authorization_metric_member",
        "adapter_correctness_denominator",
        "family",
        "counterfactual_pair_id",
        "pair_role",
        "pair_strength",
        "semantic_variable",
        "hard_negative",
        "requirements",
        "invariants",
        "threats",
        "success_criteria",
        "failure_criteria",
        "rationale",
    }
    labels: list[CorpusLabel] = []
    for index, raw in enumerate(raw_entries):
        where = f"labels.entries[{index}]"
        if not isinstance(raw, dict):
            raise CorpusValidationError(f"{where} must be an object")
        _expect_keys(raw, expected_keys, where)
        terminal = raw["expected_terminal_classification"]
        result = raw["expected_result_category"]
        auth = raw["expected_authorization_decision"]
        physical = raw["expected_physical_validation"]
        if terminal not in TERMINAL_CLASSIFICATIONS:
            raise CorpusValidationError(f"{where} terminal classification is unknown")
        if result is not None and result not in RESULT_CATEGORIES:
            raise CorpusValidationError(f"{where} result category is unknown")
        if auth not in {None, "ALLOW", "DENY"}:
            raise CorpusValidationError(f"{where} authorization decision is unknown")
        if physical not in {None, "TARGET_VALIDATION_REJECT"}:
            raise CorpusValidationError(f"{where} physical status is unknown")
        labels.append(
            CorpusLabel(
                raw["scenario_id"],
                raw["version"],
                terminal,
                result,
                auth,
                physical,
                raw["authorization_metric_member"],
                raw["adapter_correctness_denominator"],
                _string_tuple(raw, "family", where),
                raw["counterfactual_pair_id"],
                raw["pair_role"],
                raw["pair_strength"],
                raw["semantic_variable"],
                raw["hard_negative"],
                _string_tuple(raw, "requirements", where),
                _string_tuple(raw, "invariants", where),
                _string_tuple(raw, "threats", where),
                _string_tuple(raw, "success_criteria", where),
                _string_tuple(raw, "failure_criteria", where),
                raw["rationale"],
            )
        )
    ids = [item.scenario_id for item in labels]
    if len(ids) != len(set(ids)):
        raise CorpusValidationError("label scenario IDs are not unique")
    return tuple(labels)


def validate_corpus() -> tuple[tuple[CorpusScenario, ...], tuple[CorpusLabel, ...]]:
    """Validate cross-file identity, pair membership, and label isolation."""

    scenarios = load_scenarios()
    labels = load_labels()
    scenario_ids = {item.scenario_id for item in scenarios}
    label_ids = {item.scenario_id for item in labels}
    if scenario_ids != label_ids:
        raise CorpusValidationError("scenario and label IDs differ")
    pairs: dict[str, list[CorpusLabel]] = {}
    for label in labels:
        pairs.setdefault(label.counterfactual_pair_id, []).append(label)
    for pair_id, members in pairs.items():
        if len(members) != 2 or {item.pair_role for item in members} != {"A", "B"}:
            raise CorpusValidationError(f"{pair_id} must contain one A and one B member")
    if len({label.scenario_id for members in pairs.values() for label in members}) != len(labels):
        raise CorpusValidationError("pair membership is not unique")
    prohibited_fields = {
        "label",
        "expected_outcome",
        "expected_result_category",
        "family",
        "pair_id",
        "counterfactual_pair_id",
        "hard_negative",
        "rationale",
        "author_notes",
    }
    scenario_fields = set(CorpusScenario.__dataclass_fields__)
    request_fields = set(RequestSpec.__dataclass_fields__)
    if prohibited_fields & (scenario_fields | request_fields):
        raise CorpusValidationError("label-bearing fields leaked into runtime dataclasses")
    return scenarios, labels


__all__ = [
    "CorpusLabel",
    "CorpusScenario",
    "CorpusValidationError",
    "FixtureEntry",
    "FilesystemFixture",
    "INJECTION_TYPES",
    "OPERATIONS",
    "RequestSpec",
    "RESULT_CATEGORIES",
    "TERMINAL_CLASSIFICATIONS",
    "corpus_directory",
    "load_labels",
    "load_scenarios",
    "validate_corpus",
]
