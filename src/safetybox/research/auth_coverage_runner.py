"""Canonical raw-first production authorization runner.

Ordering for every scenario is frozen as: durable reservation, held-out guard,
durable ``STARTED`` exposure marker, durable first-prediction state boundary,
public production authorization call, durable raw JSONL write, then durable
completion event.  A call can therefore never occur without a conservative
exposure marker already on disk.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol, cast

from safetybox.authorization import AuthorizationComponent, CompoundActionAuthorizer
from safetybox.capabilities import Capability
from safetybox.contracts import TaskContract
from safetybox.models import ActionRequest, PolicyDecision
from safetybox.policy import TaskContractPolicy
from safetybox.research.auth_coverage_isolation import (
    RuntimeOnlyPackage,
    install_import_gate,
)
from safetybox.research.auth_coverage_raw import (
    JsonObject,
    RawAuthorizationError,
    RawAuthorizationOutput,
    RawAuthorizationRecord,
    RawComponentDecision,
    RawImplementationProvenance,
    RawMatchedCapability,
    build_raw_record,
    canonical_sha256,
    capture_authorization_input,
    raw_record_from_json,
    raw_record_json,
)
from safetybox.research.auth_coverage_state import (
    RunManifest,
    RunState,
    RunStateStore,
    canonical_json,
    exclusive_run_lock,
    sha256_file,
)
from safetybox.research.exposure_ledger import (
    ExposureBinding,
    ExposureEvent,
    ExposureEventType,
    ExposureLedger,
    new_exposure_token,
    zero_exposure_gate,
)

RUNNER_ID = "AUTH-COVERAGE-002-RUNNER@1"
RAW_MANIFEST_ID = "AUTH-COVERAGE-002-RAW-MANIFEST@1"
PARTIAL_RAW_MANIFEST_ID = "AUTH-COVERAGE-002-PARTIAL-RAW-MANIFEST@1"


class RunnerError(RuntimeError):
    """Base error for failures in the experiment harness."""


class HeldOutExecutionForbidden(RunnerError):
    """A held-out call did not have the exact canonical governance context."""


class RawPersistenceError(RunnerError):
    """A raw result could not be durably appended."""


class InjectedCrash(BaseException):
    """DEV-only abrupt-stop simulation that bypasses ordinary error recovery."""


class CrashPoint(StrEnum):
    BEFORE_RESERVATION = "BEFORE_RESERVATION"
    AFTER_RESERVATION = "AFTER_RESERVATION"
    IMMEDIATELY_BEFORE_PRODUCTION_CALL = "IMMEDIATELY_BEFORE_PRODUCTION_CALL"
    IMMEDIATELY_AFTER_PRODUCTION_CALL = "IMMEDIATELY_AFTER_PRODUCTION_CALL"
    DURING_RAW_SERIALIZATION = "DURING_RAW_SERIALIZATION"
    AFTER_RAW_WRITE = "AFTER_RAW_WRITE"
    BEFORE_FSYNC = "BEFORE_FSYNC"
    AFTER_FSYNC = "AFTER_FSYNC"
    BEFORE_COMPLETION_EVENT = "BEFORE_COMPLETION_EVENT"
    AFTER_COMPLETION_EVENT = "AFTER_COMPLETION_EVENT"
    DURING_SEALING = "DURING_SEALING"
    DURING_SCORING = "DURING_SCORING"


CrashHook = Callable[[CrashPoint], None]


def no_crash(_: CrashPoint) -> None:
    """Default hook used by canonical runs."""


class Authorizer(Protocol):
    def authorize(self, request: ActionRequest) -> PolicyDecision: ...


AuthorizerFactory = Callable[[TaskContract, tuple[AuthorizationComponent, ...]], Authorizer]


@dataclass(frozen=True, slots=True)
class RuntimeScenario:
    """Minimal execution-visible scenario; IDs are correlation values only."""

    scenario_id: str
    tool_class: str
    contract_task_id: str
    contract_description: str
    capabilities: tuple[Capability, ...]
    request: ActionRequest
    additional_components: tuple[AuthorizationComponent, ...] = ()

    def __post_init__(self) -> None:
        if not self.scenario_id or not self.tool_class or not self.contract_task_id:
            raise ValueError("runtime scenario identity fields must not be empty")
        if self.contract_task_id != self.request.task_id:
            # A mismatch is valid benchmark input, but the contract field itself must
            # remain authoritative.  Request task binding may intentionally differ.
            return


def runtime_scenario_from_mapping(value: object) -> RuntimeScenario:
    """Parse the frozen execution-visible schema with no ignored fields."""
    if not isinstance(value, Mapping):
        raise RunnerError("runtime scenario must be an object")
    allowed = {
        "scenario_id",
        "tool_class",
        "contract_task_id",
        "contract_description",
        "capabilities",
        "request",
        "additional_components",
    }
    if set(value) != allowed:
        raise RunnerError("runtime scenario fields differ from frozen schema")
    capability_values = value["capabilities"]
    component_values = value["additional_components"]
    if not isinstance(capability_values, list) or not isinstance(component_values, list):
        raise RunnerError("runtime capabilities/components must be arrays")
    capabilities: list[Capability] = []
    for item in capability_values:
        if not isinstance(item, Mapping) or set(item) != {"action", "resource"}:
            raise RunnerError("runtime capability fields differ from frozen schema")
        if not isinstance(item["action"], str) or not isinstance(item["resource"], str):
            raise RunnerError("runtime capability values must be strings")
        capabilities.append(Capability(item["action"], item["resource"]))
    components: list[AuthorizationComponent] = []
    for item in component_values:
        if not isinstance(item, Mapping) or set(item) != {"name", "request"}:
            raise RunnerError("runtime component fields differ from frozen schema")
        if not isinstance(item["name"], str):
            raise RunnerError("runtime component name must be a string")
        components.append(
            AuthorizationComponent(item["name"], _request_from_mapping(item["request"]))
        )
    identity = (
        value["scenario_id"],
        value["tool_class"],
        value["contract_task_id"],
        value["contract_description"],
    )
    if any(not isinstance(item, str) for item in identity):
        raise RunnerError("runtime scenario identity values must be strings")
    return RuntimeScenario(
        scenario_id=cast(str, value["scenario_id"]),
        tool_class=cast(str, value["tool_class"]),
        contract_task_id=cast(str, value["contract_task_id"]),
        contract_description=cast(str, value["contract_description"]),
        capabilities=tuple(capabilities),
        request=_request_from_mapping(value["request"]),
        additional_components=tuple(components),
    )


def _request_from_mapping(value: object) -> ActionRequest:
    allowed = {
        "request_id",
        "session_id",
        "task_id",
        "actor",
        "action",
        "resource",
        "arguments",
    }
    if not isinstance(value, Mapping) or set(value) != allowed:
        raise RunnerError("runtime request fields differ from frozen schema")
    text_fields = allowed - {"arguments"}
    if any(not isinstance(value[field], str) for field in text_fields) or not isinstance(
        value["arguments"], Mapping
    ):
        raise RunnerError("runtime request values differ from frozen schema")
    return ActionRequest(
        request_id=cast(str, value["request_id"]),
        session_id=cast(str, value["session_id"]),
        task_id=cast(str, value["task_id"]),
        actor=cast(str, value["actor"]),
        action=cast(str, value["action"]),
        resource=cast(str, value["resource"]),
        arguments=cast(Mapping[str, object], value["arguments"]),
    )


@dataclass(frozen=True, slots=True)
class ExposureContext:
    experiment_id: str
    corpus_id: str
    split: str
    run_id: str
    scenario_id: str
    component: str
    implementation_sha: str
    token: str
    purpose: str


@dataclass(slots=True)
class _InvocationPermit:
    binding: ExposureBinding
    consumed: bool = False

    def consume(self, binding: ExposureBinding) -> None:
        if self.consumed or self.binding != binding:
            raise HeldOutExecutionForbidden("single-use production-call permit is invalid")
        self.consumed = True


def _default_factory(
    contract: TaskContract, components: tuple[AuthorizationComponent, ...]
) -> Authorizer:
    production = TaskContractPolicy(contract)
    if components:
        return CompoundActionAuthorizer(production, components)
    return production


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _call_guard(
    *,
    context: ExposureContext,
    manifest: RunManifest,
    ledger: ExposureLedger,
) -> None:
    exact = (
        context.experiment_id == manifest.experiment_id
        and context.corpus_id == manifest.corpus_id
        and context.split == manifest.split
        and context.run_id == manifest.run_id
        and context.component == manifest.production_component
        and context.implementation_sha == manifest.implementation_sha
    )
    binding = ExposureBinding(
        experiment_id=context.experiment_id,
        corpus_id=context.corpus_id,
        split=context.split,
        run_id=context.run_id,
        scenario_id=context.scenario_id,
        component=context.component,
        implementation_sha=context.implementation_sha,
        token=context.token,
    )
    started = any(
        event.event_type is ExposureEventType.STARTED and event.binding == binding
        for event in ledger.events()
    )
    if not exact or not started:
        raise HeldOutExecutionForbidden("production call lacks exact durable exposure binding")
    if manifest.split.upper() in {"HELD_OUT", "HELDOUT"}:
        if context.purpose != "CANONICAL_RUN":
            raise HeldOutExecutionForbidden("held-out production requires canonical run mode")
        if "PYTEST_CURRENT_TEST" in os.environ:
            raise HeldOutExecutionForbidden("pytest may not execute held-out production inputs")


def invoke_governed_production(
    *,
    authorizer: Authorizer,
    request: ActionRequest,
    context: ExposureContext,
    manifest: RunManifest,
    ledger: ExposureLedger,
    permit: _InvocationPermit,
) -> PolicyDecision:
    """The only runner path across the protected production-call boundary."""
    _call_guard(context=context, manifest=manifest, ledger=ledger)
    binding = ExposureBinding(
        experiment_id=context.experiment_id,
        corpus_id=context.corpus_id,
        split=context.split,
        run_id=context.run_id,
        scenario_id=context.scenario_id,
        component=context.component,
        implementation_sha=context.implementation_sha,
        token=context.token,
    )
    permit.consume(binding)
    result = authorizer.authorize(request)
    if not isinstance(result, PolicyDecision):
        raise RunnerError("production authorization returned a malformed result")
    return result


class RawRecordWriter:
    """Append-only canonical JSONL writer with per-record fsync."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def records(self) -> tuple[RawAuthorizationRecord, ...]:
        if not self.path.exists():
            return ()
        values: list[RawAuthorizationRecord] = []
        with self.path.open("rb") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_SH)
            data = stream.read()
        if data and not data.endswith(b"\n"):
            raise RawPersistenceError("raw JSONL ends with an incomplete record")
        for line in data.splitlines():
            values.append(raw_record_from_json(line))
        return tuple(values)

    def append(self, record: RawAuthorizationRecord, crash_hook: CrashHook = no_crash) -> None:
        crash_hook(CrashPoint.DURING_RAW_SERIALIZATION)
        line = raw_record_json(record) + b"\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existed = self.path.exists()
        descriptor = os.open(self.path, os.O_RDWR | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            with os.fdopen(descriptor, "r+b") as stream:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
                stream.seek(0)
                current = stream.read()
                if current and not current.endswith(b"\n"):
                    raise RawPersistenceError("raw JSONL contains an incomplete record")
                existing = tuple(raw_record_from_json(item) for item in current.splitlines())
                if record.monotonic_sequence != len(existing):
                    raise RawPersistenceError("raw monotonic sequence is not contiguous")
                if any(item.scenario_id == record.scenario_id for item in existing):
                    raise RawPersistenceError("duplicate scenario raw record")
                stream.seek(0, os.SEEK_END)
                stream.write(line)
                crash_hook(CrashPoint.AFTER_RAW_WRITE)
                stream.flush()
                crash_hook(CrashPoint.BEFORE_FSYNC)
                os.fsync(stream.fileno())
                crash_hook(CrashPoint.AFTER_FSYNC)
            if not existed:
                _fsync_directory(self.path.parent)
        except BaseException:
            try:
                os.close(descriptor)
            except OSError:
                pass
            raise


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _matched_capability(
    decision: PolicyDecision, capabilities: Sequence[Capability], contract_task_id: str
) -> RawMatchedCapability | None:
    candidate = decision.metadata.get("applicable_capability")
    if not isinstance(candidate, Mapping):
        return None
    action = candidate.get("action")
    resource = candidate.get("resource")
    if not isinstance(action, str) or not isinstance(resource, str):
        return None
    index = next(
        (
            position
            for position, capability in enumerate(capabilities)
            if capability.action == action and capability.resource == resource
        ),
        None,
    )
    representation = {
        "action": action,
        "resource": resource,
        "scope": resource,
        "task_binding": contract_task_id,
    }
    digest = hashlib.sha256(canonical_json(representation)).hexdigest()
    return RawMatchedCapability(index, digest, action, resource, contract_task_id)


def _matched_from_mapping(
    value: object, capabilities: Sequence[Capability], contract_task_id: str
) -> RawMatchedCapability | None:
    if not isinstance(value, Mapping):
        return None
    action = value.get("action")
    resource = value.get("resource")
    if not isinstance(action, str) or not isinstance(resource, str):
        return None
    index = next(
        (
            position
            for position, capability in enumerate(capabilities)
            if capability.action == action and capability.resource == resource
        ),
        None,
    )
    representation = {
        "action": action,
        "resource": resource,
        "scope": resource,
        "task_binding": contract_task_id,
    }
    return RawMatchedCapability(
        index,
        hashlib.sha256(canonical_json(representation)).hexdigest(),
        action,
        resource,
        contract_task_id,
    )


def _output_from_decision(
    decision: PolicyDecision,
    scenario: RuntimeScenario,
) -> RawAuthorizationOutput:
    matched = _matched_capability(decision, scenario.capabilities, scenario.contract_task_id)
    authority_source_value = decision.metadata.get("authority_source")
    authority_source = (
        authority_source_value if isinstance(authority_source_value, str) else "TaskContract"
    )
    subdecisions = decision.metadata.get("subdecisions")
    components: tuple[RawComponentDecision, ...]
    if isinstance(subdecisions, Sequence) and not isinstance(subdecisions, str | bytes):
        parsed: list[RawComponentDecision] = []
        for index, item in enumerate(subdecisions):
            if not isinstance(item, Mapping):
                raise RunnerError("compound production subdecision is malformed")
            component = item.get("component", "primary" if index == 0 else f"component-{index}")
            observed = item.get("decision")
            if not isinstance(component, str) or observed not in {
                "ALLOW",
                "DENY",
                "DECISION_UNKNOWN",
            }:
                raise RunnerError("compound production subdecision is malformed")
            rule = item.get("rule_id")
            reason = item.get("reason")
            source = item.get("authority_source")
            component_match = _matched_from_mapping(
                item.get("applicable_capability"),
                scenario.capabilities,
                scenario.contract_task_id,
            )
            parsed.append(
                RawComponentDecision(
                    index=index,
                    component=component,
                    decision=cast(str, observed),
                    rule_id=rule if isinstance(rule, str) else None,
                    reason_code=rule if isinstance(rule, str) else None,
                    reason=reason if isinstance(reason, str) else None,
                    matched_capability=component_match,
                    authority_source=source if isinstance(source, str) else "TaskContract",
                    metadata=cast(JsonObject, dict(item)),
                )
            )
        components = tuple(parsed)
    else:
        components = (
            RawComponentDecision(
                index=0,
                component="primary",
                decision=decision.decision.value,
                rule_id=decision.rule_id,
                reason_code=decision.rule_id,
                reason=decision.reason,
                matched_capability=matched,
                authority_source=authority_source,
                metadata=cast(JsonObject, dict(decision.metadata)),
            ),
        )
    return RawAuthorizationOutput(
        component_decisions=components,
        final_decision=decision.decision.value,
        rule_id=decision.rule_id,
        reason_code=decision.rule_id,
        reason=decision.reason,
        matched_capability=matched,
        authority_source=authority_source,
        authority_provenance={
            "authority_source": authority_source,
            "contract_identity": scenario.contract_task_id,
            "capability_digest": matched.capability_digest if matched else None,
        },
    )


def _unknown_output(error: Exception, scenario: RuntimeScenario) -> RawAuthorizationOutput:
    components: list[RawComponentDecision] = []
    audit_metadata = getattr(error, "audit_metadata", None)
    subdecisions = (
        audit_metadata.get("subdecisions") if isinstance(audit_metadata, Mapping) else None
    )
    if isinstance(subdecisions, Sequence) and not isinstance(subdecisions, str | bytes):
        for index, item in enumerate(subdecisions):
            if not isinstance(item, Mapping):
                continue
            observed = item.get("decision")
            decision_value = (
                cast(str, observed)
                if observed in {"ALLOW", "DENY"}
                else "DECISION_UNKNOWN"
            )
            component = item.get("component", "primary" if index == 0 else f"component-{index}")
            components.append(
                RawComponentDecision(
                    index=index,
                    component=component if isinstance(component, str) else f"component-{index}",
                    decision=decision_value,
                    rule_id=(
                        cast(str, item["rule_id"])
                        if isinstance(item.get("rule_id"), str)
                        else None
                    ),
                    reason_code=(
                        cast(str, item["rule_id"])
                        if isinstance(item.get("rule_id"), str)
                        else None
                    ),
                    reason=(
                        cast(str, item["reason"])
                        if isinstance(item.get("reason"), str)
                        else None
                    ),
                    matched_capability=_matched_from_mapping(
                        item.get("applicable_capability"),
                        scenario.capabilities,
                        scenario.contract_task_id,
                    ),
                    authority_source=(
                        cast(str, item["authority_source"])
                        if isinstance(item.get("authority_source"), str)
                        else "TaskContract"
                    ),
                    metadata=cast(JsonObject, dict(item)),
                )
            )
    return RawAuthorizationOutput(
        component_decisions=tuple(components),
        final_decision="DECISION_UNKNOWN",
        rule_id=None,
        reason_code="PRODUCTION_AUTHORIZATION_ERROR",
        reason=None,
        matched_capability=None,
        authority_source=None,
        authority_provenance={},
        error=RawAuthorizationError(
            state="PRODUCTION_ERROR",
            error_type=type(error).__name__,
            message=str(error),
            call_began=True,
        ),
    )


class CanonicalAuthorizationRunner:
    """Sequential one-shot executor over a frozen label-free manifest."""

    def __init__(
        self,
        *,
        manifest: RunManifest,
        implementation: RawImplementationProvenance,
        state: RunStateStore,
        ledger: ExposureLedger,
        raw_writer: RawRecordWriter,
        implementation_sha_provider: Callable[[], str],
        purpose: str,
        authorizer_factory: AuthorizerFactory | None = None,
    ) -> None:
        if manifest.runner_version != RUNNER_ID:
            raise RunnerError("run manifest is bound to another runner version")
        if ledger.path.resolve() != Path(manifest.exposure_ledger_path).resolve():
            raise RunnerError("exposure ledger path differs from the frozen run manifest")
        expected_purpose = {
            "DEV": "DEV_EXECUTION",
            "VALIDATION": "VALIDATION_EXECUTION",
            "HELD_OUT": "CANONICAL_RUN",
        }[manifest.split]
        if purpose != expected_purpose:
            raise RunnerError("execution purpose does not match the frozen split")
        if authorizer_factory is not None and manifest.split == "HELD_OUT":
            raise RunnerError("held-out execution forbids custom production test seams")
        manifest.verify_bound_files(implementation_sha=implementation_sha_provider())
        expected_artifacts = dict(manifest.implementation_artifacts)
        if (
            implementation.production_git_sha != manifest.implementation_sha
            or dict(implementation.source_artifact_checksums) != expected_artifacts
            or implementation.policy_version != manifest.policy_version
            or implementation.authorization_spec_version
            != manifest.authorization_spec_version
            or implementation.task_contract_schema_version
            != manifest.task_contract_schema_version
            or implementation.runner_git_sha != manifest.runner_sha
            or implementation.runner_version != manifest.runner_version
        ):
            raise RunnerError("raw implementation provenance does not match run manifest")
        RuntimeOnlyPackage(Path(manifest.runtime_package_path).parent).validate()
        if manifest.split == "HELD_OUT":
            if os.environ.get("SAFETYBOX_CANONICAL_EXECUTION_PROCESS") != "1":
                raise RunnerError("held-out execution requires the fresh canonical process")
            if "PYTEST_CURRENT_TEST" in os.environ:
                raise RunnerError("ordinary pytest may not initialize held-out execution")
            install_import_gate()
            if ledger.run_has_exposure(
                experiment_id=manifest.experiment_id,
                run_id=manifest.run_id,
            ):
                snapshot = state.load()
                if snapshot.state is RunState.RUNNING_EXPOSED:
                    exposed_scenario = next(
                        event.binding.scenario_id
                        for event in reversed(ledger.events())
                        if event.event_type is ExposureEventType.STARTED
                        and event.binding.experiment_id == manifest.experiment_id
                        and event.binding.run_id == manifest.run_id
                    )
                    state.mark_partial(
                        exposed_scenario,
                        "PROCESS_RESTART_AFTER_PREDICTION_EXPOSURE",
                    )
                raise RunnerError("canonical run cannot restart after first prediction")
            zero_exposure_gate(
                ledger,
                experiment_id=manifest.experiment_id,
                corpus_id=manifest.corpus_id,
                split=manifest.split,
                component=manifest.production_component,
            )
        self.manifest = manifest
        self.implementation = implementation
        self.state = state
        self.ledger = ledger
        self.raw_writer = raw_writer
        self.implementation_sha_provider = implementation_sha_provider
        self.purpose = purpose
        self.authorizer_factory = authorizer_factory or _default_factory

    def execute_scenario(
        self,
        scenario: RuntimeScenario,
        *,
        crash_hook: CrashHook = no_crash,
        token: str | None = None,
    ) -> RawAuthorizationRecord:
        with exclusive_run_lock(self.state.path):
            return self._execute_scenario_locked(
                scenario,
                crash_hook=crash_hook,
                token=token,
            )

    def _execute_scenario_locked(
        self,
        scenario: RuntimeScenario,
        *,
        crash_hook: CrashHook,
        token: str | None,
    ) -> RawAuthorizationRecord:
        self.state.require_prediction_allowed()
        implementation_sha = self.implementation_sha_provider()
        self.manifest.verify_bound_files(implementation_sha=implementation_sha)
        records = self.raw_writer.records()
        sequence = len(records)
        if sequence >= self.manifest.scenario_count:
            raise RunnerError("frozen scenario order is already exhausted")
        if scenario.scenario_id != self.manifest.scenario_order[sequence]:
            raise RunnerError("scenario does not match the next frozen manifest position")
        auth_input = capture_authorization_input(
            tool_class=scenario.tool_class,
            contract_task_id=scenario.contract_task_id,
            contract_description=scenario.contract_description,
            received_capabilities=scenario.capabilities,
            primary_request=scenario.request,
            additional_components=scenario.additional_components,
        )
        expected_input_digest = dict(self.manifest.scenario_input_digests)[scenario.scenario_id]
        if canonical_sha256(auth_input) != expected_input_digest:
            raise RunnerError("runtime scenario input differs from its frozen package binding")
        binding = ExposureBinding(
            experiment_id=self.manifest.experiment_id,
            corpus_id=self.manifest.corpus_id,
            split=self.manifest.split,
            run_id=self.manifest.run_id,
            scenario_id=scenario.scenario_id,
            component=self.manifest.production_component,
            implementation_sha=self.manifest.implementation_sha,
            token=token or new_exposure_token(),
        )
        context = ExposureContext(**binding.to_dict(), purpose=self.purpose)
        crash_hook(CrashPoint.BEFORE_RESERVATION)
        if self.manifest.split == "HELD_OUT":
            self.ledger.reserve_canonical_scope(binding, details={"runner_id": RUNNER_ID})
        else:
            self.ledger.reserve(binding, details={"runner_id": RUNNER_ID})
        crash_hook(CrashPoint.AFTER_RESERVATION)
        crash_hook(CrashPoint.IMMEDIATELY_BEFORE_PRODUCTION_CALL)
        self.ledger.mark_started(binding, details={"call_status": "MAY_HAVE_BEGUN"})
        self.state.mark_call_boundary(scenario.scenario_id)
        permit = _InvocationPermit(binding)

        contract = TaskContract(
            scenario.contract_task_id,
            scenario.contract_description,
            scenario.capabilities,
        )
        authorizer = self.authorizer_factory(contract, scenario.additional_components)
        start = _utc_now()
        production_error: Exception | None = None
        try:
            decision = invoke_governed_production(
                authorizer=authorizer,
                request=scenario.request,
                context=context,
                manifest=self.manifest,
                ledger=self.ledger,
                permit=permit,
            )
            output = _output_from_decision(decision, scenario)
        except Exception as error:
            production_error = error
            output = _unknown_output(error, scenario)
        crash_hook(CrashPoint.IMMEDIATELY_AFTER_PRODUCTION_CALL)
        finish = _utc_now()
        record = build_raw_record(
            experiment_id=self.manifest.experiment_id,
            run_id=self.manifest.run_id,
            scenario_id=scenario.scenario_id,
            implementation=self.implementation,
            authorization_input=auth_input,
            authorization_output=output,
            start_timestamp=start,
            finish_timestamp=finish,
            monotonic_sequence=sequence,
        )
        try:
            self.raw_writer.append(record, crash_hook)
        except Exception as error:
            self.ledger.fail_after_call(
                binding,
                details={"error_type": "RAW_PERSISTENCE_ERROR", "message": str(error)},
            )
            self.state.mark_partial(scenario.scenario_id, "RAW_PERSISTENCE_ERROR")
            raise RawPersistenceError("raw result was not durably persisted") from error
        crash_hook(CrashPoint.BEFORE_COMPLETION_EVENT)
        if production_error is not None:
            self.ledger.fail_after_call(
                binding,
                details={
                    "error_type": type(production_error).__name__,
                    "decision": "DECISION_UNKNOWN",
                },
            )
            self.state.mark_partial(scenario.scenario_id, "PRODUCTION_ERROR")
            return record
        self.ledger.complete(
            binding,
            details={"record_digest": record.record_digest, "raw_sequence": sequence},
        )
        crash_hook(CrashPoint.AFTER_COMPLETION_EVENT)
        return record

    def seal_raw(
        self,
        *,
        raw_manifest_path: Path,
        run_metadata_path: Path,
        crash_hook: CrashHook = no_crash,
    ) -> dict[str, object]:
        with exclusive_run_lock(self.state.path):
            return self._seal_raw_locked(
                raw_manifest_path=raw_manifest_path,
                run_metadata_path=run_metadata_path,
                crash_hook=crash_hook,
            )

    def _seal_raw_locked(
        self,
        *,
        raw_manifest_path: Path,
        run_metadata_path: Path,
        crash_hook: CrashHook,
    ) -> dict[str, object]:
        current_state = self.state.load().state
        if current_state not in {
            RunState.RUNNING_EXPOSED,
            RunState.COMPLETED_RAW,
            RunState.SEALED_RAW,
        }:
            raise RunnerError(f"raw sealing is forbidden while run is {current_state}")
        if current_state is RunState.SEALED_RAW and raw_manifest_path.exists():
            if not verify_raw_seal(
                raw_manifest_path=raw_manifest_path,
                raw_path=self.raw_writer.path,
                ledger=self.ledger,
                run_metadata_path=run_metadata_path,
            ):
                raise RunnerError("existing sealed raw package failed verification")
            return load_raw_manifest(raw_manifest_path)
        records = self.raw_writer.records()
        _validate_evidence(
            manifest=self.manifest,
            implementation=self.implementation,
            records=records,
            ledger=self.ledger,
            require_complete=True,
        )
        if len(records) != self.manifest.scenario_count:
            raise RunnerError("cannot seal an incomplete raw package")
        if self.ledger.incomplete_exposure_count(
            experiment_id=self.manifest.experiment_id, run_id=self.manifest.run_id
        ):
            raise RunnerError("cannot seal while exposure events are incomplete")
        if current_state is RunState.RUNNING_EXPOSED:
            self.state.transition(RunState.COMPLETED_RAW)
        crash_hook(CrashPoint.DURING_SEALING)
        ledger_snapshot = _snapshot_ledger(self.ledger, raw_manifest_path.parent)
        metadata = {
            "raw_manifest_id": RAW_MANIFEST_ID,
            "record_count": len(records),
            "raw_package_checksum": sha256_file(self.raw_writer.path),
            "ledger_snapshot": ledger_snapshot.path.name,
            "ledger_checksum": sha256_file(ledger_snapshot.path),
            "ledger_anchor_checksum": sha256_file(ledger_snapshot.anchor_path),
            "ledger_head": ledger_snapshot.head,
            "ledger_event_count": ledger_snapshot.event_count,
            "run_metadata_checksum": sha256_file(run_metadata_path),
            "run_manifest_digest": self.manifest.digest,
        }
        payload = canonical_json(metadata) + b"\n"
        if raw_manifest_path.exists():
            if raw_manifest_path.read_bytes() != payload:
                raise RunnerError("existing raw manifest differs from recomputed seal")
        else:
            _write_new_durable(raw_manifest_path, payload)
        if self.state.load().state is RunState.COMPLETED_RAW:
            self.state.transition(RunState.SEALED_RAW)
        return metadata

    def seal_partial_raw(
        self,
        *,
        partial_manifest_path: Path,
        run_metadata_path: Path,
    ) -> dict[str, object]:
        """Anchor all available evidence for a terminal interrupted run.

        A partial seal is deliberately not ``SEALED_RAW`` and can never enter
        scoring.  It exists so records 0..N and their exposure history cannot be
        silently replaced while the terminal run is retained.
        """
        with exclusive_run_lock(self.state.path):
            if self.state.load().state is not RunState.PARTIAL_AFTER_PREDICTION_EXPOSURE:
                raise RunnerError(
                    "partial raw seal requires terminal partial-after-exposure state"
                )
            integrity = self.ledger.verify_integrity()
            if not integrity.valid:
                raise RunnerError("cannot partial-seal an invalid exposure ledger")
            records = self.raw_writer.records()
            _validate_evidence(
                manifest=self.manifest,
                implementation=self.implementation,
                records=records,
                ledger=self.ledger,
                require_complete=False,
            )
            ledger_snapshot = _snapshot_ledger(self.ledger, partial_manifest_path.parent)
            metadata: dict[str, object] = {
                "raw_manifest_id": PARTIAL_RAW_MANIFEST_ID,
                "complete_for_scoring": False,
                "record_count": len(records),
                "raw_package_checksum": (
                    sha256_file(self.raw_writer.path)
                    if self.raw_writer.path.exists()
                    else hashlib.sha256(b"").hexdigest()
                ),
                "ledger_snapshot": ledger_snapshot.path.name,
                "ledger_checksum": sha256_file(ledger_snapshot.path),
                "ledger_anchor_checksum": sha256_file(ledger_snapshot.anchor_path),
                "ledger_head": integrity.head,
                "ledger_event_count": integrity.event_count,
                "run_metadata_checksum": sha256_file(run_metadata_path),
                "run_manifest_digest": self.manifest.digest,
                "run_state": RunState.PARTIAL_AFTER_PREDICTION_EXPOSURE.value,
            }
            _write_new_durable(partial_manifest_path, canonical_json(metadata) + b"\n")
            return metadata


def _write_new_durable(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    _fsync_directory(path.parent)


def _snapshot_ledger(ledger: ExposureLedger, destination: Path) -> ExposureLedger:
    try:
        return ledger.snapshot_to(destination / "exposure_ledger.snapshot.jsonl")
    except ValueError as error:
        raise RunnerError("sealed ledger snapshot failed integrity verification") from error


def _validate_evidence(
    *,
    manifest: RunManifest,
    implementation: RawImplementationProvenance,
    records: Sequence[RawAuthorizationRecord],
    ledger: ExposureLedger,
    require_complete: bool,
) -> None:
    integrity = ledger.verify_integrity()
    if not integrity.valid:
        raise RunnerError("exposure ledger integrity failed before raw seal")
    if tuple(record.monotonic_sequence for record in records) != tuple(range(len(records))):
        raise RunnerError("raw sequence is not contiguous")
    if tuple(record.scenario_id for record in records) != manifest.scenario_order[: len(records)]:
        raise RunnerError("raw records do not follow frozen scenario order")
    expected_inputs = dict(manifest.scenario_input_digests)
    expected_artifacts = dict(manifest.implementation_artifacts)
    record_by_scenario = {record.scenario_id: record for record in records}
    for record in records:
        if (
            record.experiment_id != manifest.experiment_id
            or record.run_id != manifest.run_id
            or record.input_digest != expected_inputs.get(record.scenario_id)
            or record.implementation != implementation
            or dict(record.implementation.source_artifact_checksums) != expected_artifacts
        ):
            raise RunnerError("raw record binding/provenance differs from frozen manifest")
    histories: dict[str, list[ExposureEvent]] = {}
    for event in ledger.events():
        if (
            event.binding.experiment_id == manifest.experiment_id
            and event.binding.run_id == manifest.run_id
        ):
            if (
                event.binding.corpus_id != manifest.corpus_id
                or event.binding.split != manifest.split
                or event.binding.component != manifest.production_component
                or event.binding.implementation_sha != manifest.implementation_sha
            ):
                raise RunnerError("exposure binding differs from frozen run manifest")
            histories.setdefault(event.binding.scenario_id, []).append(event)
    for scenario_id, history in histories.items():
        starts = [event for event in history if event.event_type is ExposureEventType.STARTED]
        before_terminal = any(
            event.event_type
            in {ExposureEventType.FAILED_BEFORE_CALL, ExposureEventType.ABORTED_BEFORE_CALL}
            for event in history
        )
        if len(starts) != 1:
            if not require_complete and not starts and before_terminal:
                if scenario_id in record_by_scenario:
                    raise RunnerError("before-call reservation cannot have a raw record")
                continue
            raise RunnerError("each exposed scenario must have exactly one STARTED event")
        scenario_record = record_by_scenario.get(scenario_id)
        completions = [
            event for event in history if event.event_type is ExposureEventType.COMPLETED
        ]
        failures = [
            event for event in history if event.event_type is ExposureEventType.FAILED_AFTER_CALL
        ]
        if scenario_record is not None:
            if len(completions) == 1:
                completion = completions[0]
                if (
                    completion.details.get("record_digest") != scenario_record.record_digest
                    or completion.details.get("raw_sequence")
                    != scenario_record.monotonic_sequence
                ):
                    raise RunnerError("completion event does not bind the persisted raw record")
            elif require_complete:
                raise RunnerError("raw record lacks exactly one completion event")
        if require_complete and (len(completions) != 1 or failures):
            raise RunnerError("complete raw seal contains incomplete exposure evidence")
    if require_complete and (
        set(histories) != set(manifest.scenario_order)
        or set(record_by_scenario) != set(manifest.scenario_order)
    ):
        raise RunnerError("complete raw seal does not cover the frozen scenario set")


def raw_package_checksum(path: Path) -> str:
    return sha256_file(path)


def load_raw_manifest(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("raw_manifest_id") != RAW_MANIFEST_ID:
        raise RunnerError("unknown raw manifest")
    return cast(dict[str, object], value)


def verify_raw_seal(
    *,
    raw_manifest_path: Path,
    raw_path: Path,
    ledger: ExposureLedger,
    run_metadata_path: Path,
) -> bool:
    """Independently verify the persisted raw-package anchors."""
    del ledger  # The seal binds its immutable point-in-time snapshot, not the live ledger.
    try:
        value = load_raw_manifest(raw_manifest_path)
        writer = RawRecordWriter(raw_path)
        manifest_value = json.loads(run_metadata_path.read_text(encoding="utf-8"))
        if not isinstance(manifest_value, dict):
            return False
        manifest = RunManifest.from_dict(manifest_value)
        snapshot_name = value["ledger_snapshot"]
        if not isinstance(snapshot_name, str) or Path(snapshot_name).name != snapshot_name:
            return False
        sealed_ledger = ExposureLedger(raw_manifest_path.parent / snapshot_name)
        integrity = sealed_ledger.verify_integrity(
            expected_head=cast(str, value["ledger_head"]),
            expected_event_count=cast(int, value["ledger_event_count"]),
        )
        records = writer.records()
        from safetybox.research.auth_coverage_reconcile import (
            verify_complete_sealed_evidence,
        )

        return (
            integrity.valid
            and len(records) == value["record_count"]
            and sha256_file(raw_path) == value["raw_package_checksum"]
            and sha256_file(sealed_ledger.path) == value["ledger_checksum"]
            and sha256_file(sealed_ledger.anchor_path) == value["ledger_anchor_checksum"]
            and sha256_file(run_metadata_path) == value["run_metadata_checksum"]
            and value["run_manifest_digest"] == manifest.digest
            and verify_complete_sealed_evidence(
                manifest=manifest,
                records=records,
                ledger=sealed_ledger,
            )
        )
    except (KeyError, OSError, TypeError, ValueError):
        return False
