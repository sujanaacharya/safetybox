"""Raw authorization evidence for the AUTH-COVERAGE-002 instrument.

``AUTH-COVERAGE-002-RAW-SCHEMA@1`` freezes a deliberately small canonical
serialization: UTF-8 JSON, lexicographically sorted object keys, no insignificant
whitespace, JSON escaping supplied by :mod:`json`, and non-finite floats rejected.
Array order is never normalized.  In particular, the capability array is the
exact order received by the execution adapter, even though the current
``TaskContract`` stores capabilities as a set internally.

The input digest covers only the production-visible authorization input.  It
does not cover ``scenario_id`` (a correlation identifier), run metadata, labels,
or scoring metadata.  The output digest covers only the captured production
result.  The record digest covers the entire raw record except itself.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass, replace
from enum import Enum
from types import MappingProxyType
from typing import TypeAlias, cast

from safetybox.authorization import AuthorizationComponent
from safetybox.capabilities import Capability
from safetybox.contracts import TaskContract
from safetybox.models import ActionRequest

RAW_SCHEMA_ID = "AUTH-COVERAGE-002-RAW-SCHEMA@1"
RAW_RECORD_VERSION = 1
CANONICAL_SERIALIZATION_ID = "AUTH-COVERAGE-002-CANONICAL-JSON@1"

JsonScalar: TypeAlias = None | bool | int | float | str
JsonValue: TypeAlias = JsonScalar | tuple["JsonValue", ...] | Mapping[str, "JsonValue"]
JsonObject: TypeAlias = Mapping[str, JsonValue]

_PROHIBITED_BENCHMARK_KEYS = frozenset(
    {
        "authority_distance",
        "difficulty",
        "error_category",
        "expected_decision",
        "family",
        "family_label",
        "oracle_output",
        "pair_id",
        "scoring_category",
        "split_derivation_logic",
    }
)


class RawSchemaError(ValueError):
    """The raw evidence does not conform to the frozen schema."""


class RawIntegrityError(RawSchemaError):
    """A recorded digest does not match independently recomputed evidence."""


def _require_text(name: str, value: str) -> None:
    if not value:
        raise RawSchemaError(f"{name} must not be empty")


def _freeze_json(value: object, *, path: str = "$") -> JsonValue:
    if value is None or isinstance(value, bool | int | str):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise RawSchemaError(f"{path} contains a non-finite float")
        return value
    if isinstance(value, Enum):
        return _freeze_json(value.value, path=path)
    if isinstance(value, Mapping):
        frozen: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise RawSchemaError(f"{path} contains a non-string object key")
            if key.casefold() in _PROHIBITED_BENCHMARK_KEYS:
                raise RawSchemaError(f"{path}.{key} is prohibited benchmark metadata")
            frozen[key] = _freeze_json(item, path=f"{path}.{key}")
        return MappingProxyType(frozen)
    if isinstance(value, list | tuple):
        return tuple(
            _freeze_json(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        )
    raise RawSchemaError(f"{path} contains unsupported value type {type(value).__name__}")


def _canonical_value(value: object) -> object:
    """Convert frozen schema values to JSON values without reordering arrays."""
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _canonical_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Enum):
        return _canonical_value(value.value)
    if isinstance(value, Mapping):
        converted: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise RawSchemaError("canonical JSON requires string object keys")
            converted[key] = _canonical_value(item)
        return converted
    if isinstance(value, list | tuple):
        return [_canonical_value(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise RawSchemaError("canonical JSON rejects non-finite floats")
    if value is None or isinstance(value, bool | int | float | str):
        return value
    raise RawSchemaError(f"canonical JSON cannot serialize {type(value).__name__}")


def canonical_json_bytes(value: object) -> bytes:
    """Return the bytes frozen by ``CANONICAL_SERIALIZATION_ID``."""
    return json.dumps(
        _canonical_value(value),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    """Return a lowercase SHA-256 hex digest of canonical JSON bytes."""
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class RawCapability:
    """One capability in the precise order received by the runner."""

    received_index: int
    action: str
    resource: str
    scope: str
    task_binding: str
    capability_digest: str

    def __post_init__(self) -> None:
        if self.received_index < 0:
            raise RawSchemaError("capability received_index must be non-negative")
        for name in ("action", "resource", "scope", "task_binding", "capability_digest"):
            _require_text(f"capability.{name}", cast(str, getattr(self, name)))
        if self.scope != self.resource:
            raise RawSchemaError("current production capability scope must equal resource")

    @classmethod
    def capture(cls, index: int, capability: Capability, task_binding: str) -> RawCapability:
        representation = {
            "action": capability.action,
            "resource": capability.resource,
            "scope": capability.resource,
            "task_binding": task_binding,
        }
        return cls(
            received_index=index,
            action=capability.action,
            resource=capability.resource,
            scope=capability.resource,
            task_binding=task_binding,
            capability_digest=canonical_sha256(representation),
        )


@dataclass(frozen=True, slots=True)
class RawRequest:
    """Every field of the current public production ``ActionRequest``."""

    request_id: str
    session_id: str
    task_id: str
    actor: str
    action: str
    resource: str
    arguments: JsonObject

    def __post_init__(self) -> None:
        for name in ("request_id", "session_id", "task_id", "actor", "action", "resource"):
            _require_text(f"request.{name}", cast(str, getattr(self, name)))
        frozen = _freeze_json(self.arguments, path="$.request.arguments")
        if not isinstance(frozen, Mapping):  # pragma: no cover - type-directed defense
            raise RawSchemaError("request arguments must be an object")
        object.__setattr__(self, "arguments", frozen)

    @classmethod
    def capture(cls, request: ActionRequest) -> RawRequest:
        return cls(
            request_id=request.request_id,
            session_id=request.session_id,
            task_id=request.task_id,
            actor=request.actor,
            action=request.action,
            resource=request.resource,
            arguments=cast(JsonObject, request.arguments),
        )

    def reconstruct(self) -> ActionRequest:
        return ActionRequest(
            request_id=self.request_id,
            session_id=self.session_id,
            task_id=self.task_id,
            actor=self.actor,
            action=self.action,
            resource=self.resource,
            arguments=self.arguments,
        )


@dataclass(frozen=True, slots=True)
class RawComponentInput:
    """An ordered named request evaluated as part of authorization."""

    index: int
    component: str
    request: RawRequest

    def __post_init__(self) -> None:
        if self.index < 0:
            raise RawSchemaError("component index must be non-negative")
        _require_text("component name", self.component)


@dataclass(frozen=True, slots=True)
class RawAuthorizationInput:
    """The complete production-visible input, with no benchmark answer key."""

    tool_class: str
    contract_task_id: str
    contract_description: str
    capabilities: tuple[RawCapability, ...]
    components: tuple[RawComponentInput, ...]

    def __post_init__(self) -> None:
        _require_text("tool_class", self.tool_class)
        _require_text("contract_task_id", self.contract_task_id)
        expected_capability_indexes = tuple(range(len(self.capabilities)))
        if tuple(item.received_index for item in self.capabilities) != expected_capability_indexes:
            raise RawSchemaError(
                "capability indexes must be contiguous and preserve received order"
            )
        if any(item.task_binding != self.contract_task_id for item in self.capabilities):
            raise RawSchemaError("every capability task binding must match the contract task")
        expected_component_indexes = tuple(range(len(self.components)))
        if tuple(item.index for item in self.components) != expected_component_indexes:
            raise RawSchemaError(
                "component indexes must be contiguous and preserve evaluated order"
            )
        if not self.components:
            raise RawSchemaError("authorization input requires a primary component")

    @property
    def primary(self) -> RawComponentInput:
        return self.components[0]


def capture_authorization_input(
    *,
    tool_class: str,
    contract_task_id: str,
    contract_description: str,
    received_capabilities: Sequence[Capability],
    primary_request: ActionRequest,
    additional_components: Sequence[AuthorizationComponent] = (),
    primary_component_name: str = "primary",
) -> RawAuthorizationInput:
    """Capture input before policy construction can discard capability order."""
    components = (
        RawComponentInput(0, primary_component_name, RawRequest.capture(primary_request)),
        *(
            RawComponentInput(index, item.name, RawRequest.capture(item.request))
            for index, item in enumerate(additional_components, start=1)
        ),
    )
    capabilities = tuple(
        RawCapability.capture(index, capability, contract_task_id)
        for index, capability in enumerate(received_capabilities)
    )
    return RawAuthorizationInput(
        tool_class=tool_class,
        contract_task_id=contract_task_id,
        contract_description=contract_description,
        capabilities=capabilities,
        components=components,
    )


@dataclass(frozen=True, slots=True)
class RawMatchedCapability:
    """Stable identity and representation of the capability selected by policy."""

    received_index: int | None
    capability_digest: str
    action: str
    resource: str
    task_binding: str

    def __post_init__(self) -> None:
        if self.received_index is not None and self.received_index < 0:
            raise RawSchemaError("matched capability index must be non-negative")
        for name in ("capability_digest", "action", "resource", "task_binding"):
            _require_text(f"matched_capability.{name}", cast(str, getattr(self, name)))


@dataclass(frozen=True, slots=True)
class RawComponentDecision:
    """Structured output for one ordered authorization component."""

    index: int
    component: str
    decision: str
    rule_id: str | None
    reason_code: str | None
    reason: str | None
    matched_capability: RawMatchedCapability | None
    authority_source: str | None
    metadata: JsonObject

    def __post_init__(self) -> None:
        if self.index < 0:
            raise RawSchemaError("decision index must be non-negative")
        _require_text("decision component", self.component)
        if self.decision not in {"ALLOW", "DENY", "DECISION_UNKNOWN"}:
            raise RawSchemaError(f"unsupported component decision: {self.decision}")
        frozen = _freeze_json(self.metadata, path="$.component_decision.metadata")
        if not isinstance(frozen, Mapping):  # pragma: no cover - type-directed defense
            raise RawSchemaError("component-decision metadata must be an object")
        object.__setattr__(self, "metadata", frozen)


@dataclass(frozen=True, slots=True)
class RawAuthorizationError:
    """Truthful infrastructure or production failure; never a fabricated denial."""

    state: str
    error_type: str
    message: str
    call_began: bool

    def __post_init__(self) -> None:
        _require_text("error state", self.state)
        _require_text("error type", self.error_type)


@dataclass(frozen=True, slots=True)
class RawAuthorizationOutput:
    """Complete structured output captured from production authorization."""

    component_decisions: tuple[RawComponentDecision, ...]
    final_decision: str
    rule_id: str | None
    reason_code: str | None
    reason: str | None
    matched_capability: RawMatchedCapability | None
    authority_source: str | None
    authority_provenance: JsonObject
    error: RawAuthorizationError | None = None

    def __post_init__(self) -> None:
        if self.final_decision not in {"ALLOW", "DENY", "DECISION_UNKNOWN"}:
            raise RawSchemaError(f"unsupported final decision: {self.final_decision}")
        if self.error is not None and self.final_decision != "DECISION_UNKNOWN":
            raise RawSchemaError("an authorization error requires DECISION_UNKNOWN")
        if tuple(item.index for item in self.component_decisions) != tuple(
            range(len(self.component_decisions))
        ):
            raise RawSchemaError("component decisions must have contiguous ordered indexes")
        frozen = _freeze_json(self.authority_provenance, path="$.authority_provenance")
        if not isinstance(frozen, Mapping):  # pragma: no cover - type-directed defense
            raise RawSchemaError("authority provenance must be an object")
        object.__setattr__(self, "authority_provenance", frozen)


@dataclass(frozen=True, slots=True)
class RawImplementationProvenance:
    """Exact identities required to interpret a production prediction."""

    production_git_sha: str
    source_artifact_checksums: Mapping[str, str]
    policy_version: str
    task_contract_schema_version: str
    authorization_spec_version: str
    runner_git_sha: str
    runner_version: str

    def __post_init__(self) -> None:
        for name in (
            "production_git_sha",
            "policy_version",
            "task_contract_schema_version",
            "authorization_spec_version",
            "runner_git_sha",
            "runner_version",
        ):
            _require_text(f"implementation.{name}", cast(str, getattr(self, name)))
        checksums = dict(self.source_artifact_checksums)
        if not checksums:
            raise RawSchemaError("at least one production source checksum is required")
        for path, digest in checksums.items():
            _require_text("source artifact path", path)
            _require_text(f"source checksum for {path}", digest)
        object.__setattr__(self, "source_artifact_checksums", MappingProxyType(checksums))


@dataclass(frozen=True, slots=True)
class RawAuthorizationRecord:
    """One self-contained, reconstructable authorization observation."""

    schema_id: str
    record_version: int
    canonical_serialization: str
    experiment_id: str
    run_id: str
    scenario_id: str
    implementation: RawImplementationProvenance
    authorization_input: RawAuthorizationInput
    authorization_output: RawAuthorizationOutput
    start_timestamp: str
    finish_timestamp: str
    monotonic_sequence: int
    input_digest: str
    output_digest: str
    record_digest: str

    def __post_init__(self) -> None:
        if self.schema_id != RAW_SCHEMA_ID or self.record_version != RAW_RECORD_VERSION:
            raise RawSchemaError("unsupported raw schema identity or record version")
        if self.canonical_serialization != CANONICAL_SERIALIZATION_ID:
            raise RawSchemaError("unsupported canonical serialization")
        for name in (
            "experiment_id",
            "run_id",
            "scenario_id",
            "start_timestamp",
            "finish_timestamp",
            "input_digest",
            "output_digest",
            "record_digest",
        ):
            _require_text(name, cast(str, getattr(self, name)))
        if self.monotonic_sequence < 0:
            raise RawSchemaError("monotonic_sequence must be non-negative")
        component_inputs = self.authorization_input.components
        for decision in self.authorization_output.component_decisions:
            if decision.index >= len(component_inputs):
                raise RawSchemaError("component decision has no corresponding input")
            if decision.component != component_inputs[decision.index].component:
                raise RawSchemaError("component decision name does not match its input")
        matched_values = (
            self.authorization_output.matched_capability,
            *(
                decision.matched_capability
                for decision in self.authorization_output.component_decisions
            ),
        )
        capabilities = self.authorization_input.capabilities
        for matched in matched_values:
            if matched is None or matched.received_index is None:
                continue
            if matched.received_index >= len(capabilities):
                raise RawSchemaError("matched capability index is outside received capabilities")
            source = capabilities[matched.received_index]
            if (
                matched.capability_digest,
                matched.action,
                matched.resource,
                matched.task_binding,
            ) != (
                source.capability_digest,
                source.action,
                source.resource,
                source.task_binding,
            ):
                raise RawSchemaError("matched capability differs from its received representation")


def _record_digest_projection(record: RawAuthorizationRecord) -> Mapping[str, object]:
    return {
        field.name: getattr(record, field.name)
        for field in fields(record)
        if field.name != "record_digest"
    }


def build_raw_record(
    *,
    experiment_id: str,
    run_id: str,
    scenario_id: str,
    implementation: RawImplementationProvenance,
    authorization_input: RawAuthorizationInput,
    authorization_output: RawAuthorizationOutput,
    start_timestamp: str,
    finish_timestamp: str,
    monotonic_sequence: int,
) -> RawAuthorizationRecord:
    """Construct a raw record and compute all three independent digests."""
    input_digest = canonical_sha256(authorization_input)
    output_digest = canonical_sha256(authorization_output)
    incomplete = RawAuthorizationRecord(
        schema_id=RAW_SCHEMA_ID,
        record_version=RAW_RECORD_VERSION,
        canonical_serialization=CANONICAL_SERIALIZATION_ID,
        experiment_id=experiment_id,
        run_id=run_id,
        scenario_id=scenario_id,
        implementation=implementation,
        authorization_input=authorization_input,
        authorization_output=authorization_output,
        start_timestamp=start_timestamp,
        finish_timestamp=finish_timestamp,
        monotonic_sequence=monotonic_sequence,
        input_digest=input_digest,
        output_digest=output_digest,
        record_digest="PENDING",
    )
    return replace(
        incomplete,
        record_digest=canonical_sha256(_record_digest_projection(incomplete)),
    )


@dataclass(frozen=True, slots=True)
class ReconstructedAuthorizationInput:
    """Production domain objects rebuilt exclusively from one raw record."""

    tool_class: str
    contract: TaskContract
    received_capabilities: tuple[Capability, ...]
    primary_request: ActionRequest
    additional_components: tuple[AuthorizationComponent, ...]
    primary_component_name: str


def reconstruct_authorization_input(
    record: RawAuthorizationRecord,
) -> ReconstructedAuthorizationInput:
    """Rebuild production input without consulting the runtime scenario file."""
    raw_input = record.authorization_input
    capabilities = tuple(
        Capability(item.action, item.resource) for item in raw_input.capabilities
    )
    components = raw_input.components
    return ReconstructedAuthorizationInput(
        tool_class=raw_input.tool_class,
        contract=TaskContract(
            raw_input.contract_task_id,
            raw_input.contract_description,
            capabilities,
        ),
        received_capabilities=capabilities,
        primary_request=components[0].request.reconstruct(),
        additional_components=tuple(
            AuthorizationComponent(item.component, item.request.reconstruct())
            for item in components[1:]
        ),
        primary_component_name=components[0].component,
    )


def canonical_reconstructed_input(
    reconstructed: ReconstructedAuthorizationInput,
) -> RawAuthorizationInput:
    """Independently recapture reconstructed domain objects for digest checking."""
    return capture_authorization_input(
        tool_class=reconstructed.tool_class,
        contract_task_id=reconstructed.contract.task_id,
        contract_description=reconstructed.contract.description,
        received_capabilities=reconstructed.received_capabilities,
        primary_request=reconstructed.primary_request,
        additional_components=reconstructed.additional_components,
        primary_component_name=reconstructed.primary_component_name,
    )


def verify_raw_record(record: RawAuthorizationRecord) -> ReconstructedAuthorizationInput:
    """Verify every digest and the lossless input reconstruction invariant."""
    if canonical_sha256(record.authorization_input) != record.input_digest:
        raise RawIntegrityError("recorded input digest does not match embedded raw input")
    reconstructed = reconstruct_authorization_input(record)
    if canonical_sha256(canonical_reconstructed_input(reconstructed)) != record.input_digest:
        raise RawIntegrityError("reconstructed production input digest does not match record")
    if canonical_sha256(record.authorization_output) != record.output_digest:
        raise RawIntegrityError("recorded output digest does not match embedded raw output")
    if canonical_sha256(_record_digest_projection(record)) != record.record_digest:
        raise RawIntegrityError("record digest does not match raw record")
    return reconstructed


def raw_record_json(record: RawAuthorizationRecord) -> bytes:
    """Serialize a verified raw record as one canonical JSON line payload."""
    verify_raw_record(record)
    return canonical_json_bytes(record)


def _reject_duplicate_object_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RawSchemaError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _object(value: object, path: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise RawSchemaError(f"{path} must be an object")
    if not all(isinstance(key, str) for key in value):  # pragma: no cover - JSON defense
        raise RawSchemaError(f"{path} must have string keys")
    return cast(dict[str, object], value)


def _strict_object(
    value: object,
    expected: frozenset[str],
    path: str,
) -> dict[str, object]:
    result = _object(value, path)
    actual = frozenset(result)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise RawSchemaError(f"{path} field mismatch: missing={missing}, unknown={unknown}")
    return result


def _array(value: object, path: str) -> list[object]:
    if not isinstance(value, list):
        raise RawSchemaError(f"{path} must be an array")
    return value


def _string(value: object, path: str) -> str:
    if not isinstance(value, str):
        raise RawSchemaError(f"{path} must be a string")
    return value


def _optional_string(value: object, path: str) -> str | None:
    if value is None:
        return None
    return _string(value, path)


def _integer(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RawSchemaError(f"{path} must be an integer")
    return value


def _boolean(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise RawSchemaError(f"{path} must be a boolean")
    return value


def _json_object(value: object, path: str) -> JsonObject:
    frozen = _freeze_json(_object(value, path), path=path)
    if not isinstance(frozen, Mapping):  # pragma: no cover - type-directed defense
        raise RawSchemaError(f"{path} must be an object")
    return frozen


def _parse_capability(value: object, path: str) -> RawCapability:
    item = _strict_object(
        value,
        frozenset(
            {
                "received_index",
                "action",
                "resource",
                "scope",
                "task_binding",
                "capability_digest",
            }
        ),
        path,
    )
    return RawCapability(
        received_index=_integer(item["received_index"], f"{path}.received_index"),
        action=_string(item["action"], f"{path}.action"),
        resource=_string(item["resource"], f"{path}.resource"),
        scope=_string(item["scope"], f"{path}.scope"),
        task_binding=_string(item["task_binding"], f"{path}.task_binding"),
        capability_digest=_string(item["capability_digest"], f"{path}.capability_digest"),
    )


def _parse_request(value: object, path: str) -> RawRequest:
    item = _strict_object(
        value,
        frozenset(
            {
                "request_id",
                "session_id",
                "task_id",
                "actor",
                "action",
                "resource",
                "arguments",
            }
        ),
        path,
    )
    return RawRequest(
        request_id=_string(item["request_id"], f"{path}.request_id"),
        session_id=_string(item["session_id"], f"{path}.session_id"),
        task_id=_string(item["task_id"], f"{path}.task_id"),
        actor=_string(item["actor"], f"{path}.actor"),
        action=_string(item["action"], f"{path}.action"),
        resource=_string(item["resource"], f"{path}.resource"),
        arguments=_json_object(item["arguments"], f"{path}.arguments"),
    )


def _parse_component_input(value: object, path: str) -> RawComponentInput:
    item = _strict_object(value, frozenset({"index", "component", "request"}), path)
    return RawComponentInput(
        index=_integer(item["index"], f"{path}.index"),
        component=_string(item["component"], f"{path}.component"),
        request=_parse_request(item["request"], f"{path}.request"),
    )


def _parse_authorization_input(value: object, path: str) -> RawAuthorizationInput:
    item = _strict_object(
        value,
        frozenset(
            {
                "tool_class",
                "contract_task_id",
                "contract_description",
                "capabilities",
                "components",
            }
        ),
        path,
    )
    return RawAuthorizationInput(
        tool_class=_string(item["tool_class"], f"{path}.tool_class"),
        contract_task_id=_string(item["contract_task_id"], f"{path}.contract_task_id"),
        contract_description=_string(
            item["contract_description"], f"{path}.contract_description"
        ),
        capabilities=tuple(
            _parse_capability(raw, f"{path}.capabilities[{index}]")
            for index, raw in enumerate(_array(item["capabilities"], f"{path}.capabilities"))
        ),
        components=tuple(
            _parse_component_input(raw, f"{path}.components[{index}]")
            for index, raw in enumerate(_array(item["components"], f"{path}.components"))
        ),
    )


def _parse_matched_capability(value: object, path: str) -> RawMatchedCapability | None:
    if value is None:
        return None
    item = _strict_object(
        value,
        frozenset(
            {"received_index", "capability_digest", "action", "resource", "task_binding"}
        ),
        path,
    )
    received_index = item["received_index"]
    return RawMatchedCapability(
        received_index=(
            None
            if received_index is None
            else _integer(received_index, f"{path}.received_index")
        ),
        capability_digest=_string(item["capability_digest"], f"{path}.capability_digest"),
        action=_string(item["action"], f"{path}.action"),
        resource=_string(item["resource"], f"{path}.resource"),
        task_binding=_string(item["task_binding"], f"{path}.task_binding"),
    )


def _parse_component_decision(value: object, path: str) -> RawComponentDecision:
    item = _strict_object(
        value,
        frozenset(
            {
                "index",
                "component",
                "decision",
                "rule_id",
                "reason_code",
                "reason",
                "matched_capability",
                "authority_source",
                "metadata",
            }
        ),
        path,
    )
    return RawComponentDecision(
        index=_integer(item["index"], f"{path}.index"),
        component=_string(item["component"], f"{path}.component"),
        decision=_string(item["decision"], f"{path}.decision"),
        rule_id=_optional_string(item["rule_id"], f"{path}.rule_id"),
        reason_code=_optional_string(item["reason_code"], f"{path}.reason_code"),
        reason=_optional_string(item["reason"], f"{path}.reason"),
        matched_capability=_parse_matched_capability(
            item["matched_capability"], f"{path}.matched_capability"
        ),
        authority_source=_optional_string(
            item["authority_source"], f"{path}.authority_source"
        ),
        metadata=_json_object(item["metadata"], f"{path}.metadata"),
    )


def _parse_error(value: object, path: str) -> RawAuthorizationError | None:
    if value is None:
        return None
    item = _strict_object(
        value,
        frozenset({"state", "error_type", "message", "call_began"}),
        path,
    )
    return RawAuthorizationError(
        state=_string(item["state"], f"{path}.state"),
        error_type=_string(item["error_type"], f"{path}.error_type"),
        message=_string(item["message"], f"{path}.message"),
        call_began=_boolean(item["call_began"], f"{path}.call_began"),
    )


def _parse_authorization_output(value: object, path: str) -> RawAuthorizationOutput:
    item = _strict_object(
        value,
        frozenset(
            {
                "component_decisions",
                "final_decision",
                "rule_id",
                "reason_code",
                "reason",
                "matched_capability",
                "authority_source",
                "authority_provenance",
                "error",
            }
        ),
        path,
    )
    return RawAuthorizationOutput(
        component_decisions=tuple(
            _parse_component_decision(raw, f"{path}.component_decisions[{index}]")
            for index, raw in enumerate(
                _array(item["component_decisions"], f"{path}.component_decisions")
            )
        ),
        final_decision=_string(item["final_decision"], f"{path}.final_decision"),
        rule_id=_optional_string(item["rule_id"], f"{path}.rule_id"),
        reason_code=_optional_string(item["reason_code"], f"{path}.reason_code"),
        reason=_optional_string(item["reason"], f"{path}.reason"),
        matched_capability=_parse_matched_capability(
            item["matched_capability"], f"{path}.matched_capability"
        ),
        authority_source=_optional_string(
            item["authority_source"], f"{path}.authority_source"
        ),
        authority_provenance=_json_object(
            item["authority_provenance"], f"{path}.authority_provenance"
        ),
        error=_parse_error(item["error"], f"{path}.error"),
    )


def _parse_implementation(value: object, path: str) -> RawImplementationProvenance:
    item = _strict_object(
        value,
        frozenset(
            {
                "production_git_sha",
                "source_artifact_checksums",
                "policy_version",
                "task_contract_schema_version",
                "authorization_spec_version",
                "runner_git_sha",
                "runner_version",
            }
        ),
        path,
    )
    checksum_values = _object(
        item["source_artifact_checksums"], f"{path}.source_artifact_checksums"
    )
    checksums = {
        key: _string(value, f"{path}.source_artifact_checksums.{key}")
        for key, value in checksum_values.items()
    }
    return RawImplementationProvenance(
        production_git_sha=_string(item["production_git_sha"], f"{path}.production_git_sha"),
        source_artifact_checksums=checksums,
        policy_version=_string(item["policy_version"], f"{path}.policy_version"),
        task_contract_schema_version=_string(
            item["task_contract_schema_version"], f"{path}.task_contract_schema_version"
        ),
        authorization_spec_version=_string(
            item["authorization_spec_version"], f"{path}.authorization_spec_version"
        ),
        runner_git_sha=_string(item["runner_git_sha"], f"{path}.runner_git_sha"),
        runner_version=_string(item["runner_version"], f"{path}.runner_version"),
    )


def raw_record_from_json(payload: bytes | str) -> RawAuthorizationRecord:
    """Strictly parse and verify one independently persisted canonical record.

    A trailing JSONL newline is accepted. Duplicate keys, noncanonical JSON,
    unknown or missing schema fields, and digest failures are rejected.
    """
    try:
        text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
    except UnicodeDecodeError as error:
        raise RawSchemaError("raw record is not valid UTF-8") from error
    document = text.rstrip("\r\n")
    try:
        decoded = json.loads(document, object_pairs_hook=_reject_duplicate_object_keys)
    except (json.JSONDecodeError, RawSchemaError) as error:
        raise RawSchemaError(f"invalid raw record JSON: {error}") from error
    root = _strict_object(
        decoded,
        frozenset(
            {
                "schema_id",
                "record_version",
                "canonical_serialization",
                "experiment_id",
                "run_id",
                "scenario_id",
                "implementation",
                "authorization_input",
                "authorization_output",
                "start_timestamp",
                "finish_timestamp",
                "monotonic_sequence",
                "input_digest",
                "output_digest",
                "record_digest",
            }
        ),
        "$",
    )
    record = RawAuthorizationRecord(
        schema_id=_string(root["schema_id"], "$.schema_id"),
        record_version=_integer(root["record_version"], "$.record_version"),
        canonical_serialization=_string(
            root["canonical_serialization"], "$.canonical_serialization"
        ),
        experiment_id=_string(root["experiment_id"], "$.experiment_id"),
        run_id=_string(root["run_id"], "$.run_id"),
        scenario_id=_string(root["scenario_id"], "$.scenario_id"),
        implementation=_parse_implementation(root["implementation"], "$.implementation"),
        authorization_input=_parse_authorization_input(
            root["authorization_input"], "$.authorization_input"
        ),
        authorization_output=_parse_authorization_output(
            root["authorization_output"], "$.authorization_output"
        ),
        start_timestamp=_string(root["start_timestamp"], "$.start_timestamp"),
        finish_timestamp=_string(root["finish_timestamp"], "$.finish_timestamp"),
        monotonic_sequence=_integer(root["monotonic_sequence"], "$.monotonic_sequence"),
        input_digest=_string(root["input_digest"], "$.input_digest"),
        output_digest=_string(root["output_digest"], "$.output_digest"),
        record_digest=_string(root["record_digest"], "$.record_digest"),
    )
    verify_raw_record(record)
    if canonical_json_bytes(record) != document.encode("utf-8"):
        raise RawSchemaError("raw record is valid JSON but not frozen canonical JSON")
    return record
