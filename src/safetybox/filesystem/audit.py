"""M3-compatible filesystem audit helpers and execution lifecycle bridge."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field

from safetybox.audit import AuditRecorder
from safetybox.events import EventType, SafetyBoxEvent
from safetybox.exceptions import AuditFailure
from safetybox.filesystem.canonicalization import LOGICAL_ROOT
from safetybox.filesystem.errors import (
    FilesystemMediationError,
    FilesystemPrimitiveError,
    FilesystemToolError,
    TargetValidationError,
)
from safetybox.filesystem.mapping import LogicalHostMapper
from safetybox.filesystem.models import (
    FilesystemOperation,
    FilesystemResultCategory,
    PhysicalValidationStatus,
)
from safetybox.filesystem.primitives import RealFilesystemPrimitives
from safetybox.filesystem.state_digest import digest_manifest
from safetybox.filesystem.validation import PhysicalTargetValidator, ValidatedTargets
from safetybox.filesystem.versions import (
    FILESYSTEM_ADAPTER_VERSION,
    FILESYSTEM_AUDIT_ENVELOPE_VERSION,
    FILESYSTEM_CANONICALIZATION_VERSION,
    STATE_DIGEST_VERSION,
)
from safetybox.models import ActionRequest


def governed_requested_identifier(value: object) -> str:
    """Return a recordable logical spelling or a non-reversible governed identifier."""
    if isinstance(value, str) and "\x00" not in value:
        if (
            not value.startswith("/")
            or value == LOGICAL_ROOT
            or value.startswith(f"{LOGICAL_ROOT}/")
        ):
            return value
    encoded = repr(type(value).__name__).encode("utf-8")
    if isinstance(value, (str, bytes)):
        encoded += bytes(value, "utf-8") if isinstance(value, str) else value
    return f"governed-sha256:{hashlib.sha256(encoded).hexdigest()}"


def arguments_digest(
    operation: FilesystemOperation,
    canonical_resource: str,
    canonical_destination: str | None,
    data: bytes | None,
) -> str:
    value = {
        "action": operation.value,
        "resource": canonical_resource,
        "destination": canonical_destination,
        "data_size": None if data is None else len(data),
        "data_sha256": None if data is None else hashlib.sha256(data).hexdigest(),
    }
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(slots=True)
class FilesystemAuditBridge:
    recorder: AuditRecorder

    def emit(
        self,
        request: ActionRequest,
        event_type: EventType,
        *,
        parent_event_id: str | None,
        metadata: Mapping[str, object],
    ) -> SafetyBoxEvent:
        try:
            return self.recorder.emit(
                request,
                event_type,
                correlation_id=request.request_id,
                parent_event_id=parent_event_id,
                metadata=metadata,
            )
        except Exception as error:
            raise AuditFailure(
                "Audit recording failed before protected filesystem execution.",
                execution_may_have_started=False,
                failed_event_type=event_type.value,
            ) from error


@dataclass(slots=True)
class FilesystemExecutionBoundary:
    """Per-request validator, protected tool, and terminal-evidence provider."""

    operation: FilesystemOperation
    mapper: LogicalHostMapper
    primitives: RealFilesystemPrimitives
    audit_bridge: FilesystemAuditBridge
    canonical_destination: str | None
    base_metadata: Mapping[str, object]
    validated: ValidatedTargets | None = field(default=None, init=False)
    validation_status: PhysicalValidationStatus = field(
        default=PhysicalValidationStatus.NOT_ATTEMPTED, init=False
    )
    primitive_started: bool = field(default=False, init=False)
    pre_state_digest: str | None = field(default=None, init=False)
    post_state_digest: str | None = field(default=None, init=False)

    def before_execution(
        self,
        request: ActionRequest,
        *,
        correlation_id: str,
        parent_event_id: str,
    ) -> str:
        del correlation_id
        started = self.audit_bridge.emit(
            request,
            EventType.TARGET_VALIDATION_STARTED,
            parent_event_id=parent_event_id,
            metadata={**self.base_metadata, "physical_validation": "STARTED"},
        )
        try:
            self.validated = PhysicalTargetValidator(self.mapper, self.primitives).validate(
                self.operation, request.resource, self.canonical_destination
            )
            if self.operation in _MUTATING_OPERATIONS:
                self.pre_state_digest = digest_manifest(
                    self.mapper, self._state_scope(request.resource)
                ).digest
        except FilesystemMediationError as error:
            self.validation_status = PhysicalValidationStatus.REJECTED
            self.audit_bridge.emit(
                request,
                EventType.TARGET_VALIDATION_FAILED,
                parent_event_id=started.event_id,
                metadata={
                    **self.base_metadata,
                    "physical_validation": self.validation_status.value,
                    "error_code": error.code,
                    "result_category": self._category_for_error(error).value,
                    "execution_attempted": False,
                    "execution_succeeded": False,
                },
            )
            raise
        except Exception as error:
            self.validation_status = PhysicalValidationStatus.REJECTED
            wrapped = TargetValidationError(
                "EXP014-TARGET-VALIDATION-FAILED",
                "Physical target validation could not complete safely.",
                cause=error,
            )
            self.audit_bridge.emit(
                request,
                EventType.TARGET_VALIDATION_FAILED,
                parent_event_id=started.event_id,
                metadata={
                    **self.base_metadata,
                    "physical_validation": self.validation_status.value,
                    "error_code": wrapped.code,
                    "result_category": FilesystemResultCategory.FAIL_CLOSED.value,
                    "execution_attempted": False,
                    "execution_succeeded": False,
                },
            )
            raise wrapped from error

        self.validation_status = PhysicalValidationStatus.SUCCEEDED
        succeeded = self.audit_bridge.emit(
            request,
            EventType.TARGET_VALIDATION_SUCCEEDED,
            parent_event_id=started.event_id,
            metadata={
                **self.base_metadata,
                "physical_validation": self.validation_status.value,
                "pre_state_digest": self.pre_state_digest,
            },
        )
        return succeeded.event_id

    def execute(self, request: ActionRequest) -> object:
        targets = self.validated
        if targets is None:  # pragma: no cover - monitor ordering invariant
            raise RuntimeError("filesystem execution reached without validation")
        self.primitive_started = True
        data = request.arguments.get("data")
        if self.operation is FilesystemOperation.READ:
            return self.primitives.read(targets.source)
        if self.operation is FilesystemOperation.WRITE:
            self.primitives.write(targets.source, self._require_data(data))
            return None
        if self.operation is FilesystemOperation.APPEND:
            self.primitives.append(targets.source, self._require_data(data))
            return None
        if self.operation is FilesystemOperation.CREATE:
            self.primitives.create(targets.source, self._require_data(data))
            return None
        if self.operation is FilesystemOperation.DELETE:
            if targets.source_type is None:  # pragma: no cover - validation invariant
                raise RuntimeError("validated delete target has no type")
            if targets.source_type.value == "DIRECTORY":
                self.primitives.delete_directory(targets.source)
            else:
                self.primitives.delete_file(targets.source)
            return None
        if self.operation is FilesystemOperation.RENAME:
            if targets.destination is None:  # pragma: no cover - validation invariant
                raise RuntimeError("validated rename target has no destination")
            self.primitives.rename(targets.source, targets.destination)
            return None
        if self.operation is FilesystemOperation.MKDIR:
            self.primitives.mkdir(targets.source)
            return None
        if self.operation is FilesystemOperation.LIST:
            return self.primitives.list_directory(targets.source)
        if self.operation is FilesystemOperation.STAT:
            return self.primitives.minimized_stat(targets.source)
        raise RuntimeError("unsupported filesystem operation")  # pragma: no cover

    def after_execution_success(
        self, request: ActionRequest, result: object
    ) -> Mapping[str, object]:
        del result
        if self.operation in _MUTATING_OPERATIONS:
            self.post_state_digest = digest_manifest(
                self.mapper, self._state_scope(request.resource)
            ).digest
        return {
            "result_category": FilesystemResultCategory.ALLOW.value,
            "physical_validation": self.validation_status.value,
            "pre_state_digest": self.pre_state_digest,
            "post_state_digest": self.post_state_digest,
            "error_code": None,
        }

    def after_execution_failure(
        self, request: ActionRequest, error: Exception
    ) -> Mapping[str, object]:
        if self.operation in _MUTATING_OPERATIONS:
            try:
                self.post_state_digest = digest_manifest(
                    self.mapper, self._state_scope(request.resource)
                ).digest
            except Exception:
                self.post_state_digest = None
        category = self._category_for_error(error)
        return {
            "result_category": category.value,
            "physical_validation": self.validation_status.value,
            "pre_state_digest": self.pre_state_digest,
            "post_state_digest": self.post_state_digest,
            "error_code": getattr(error, "code", "FS-UNEXPECTED-EXECUTION-FAILURE"),
        }

    def _state_scope(self, resource: str) -> tuple[str, ...]:
        values = [resource, _logical_parent(resource)]
        if self.canonical_destination is not None:
            values.extend([self.canonical_destination, _logical_parent(self.canonical_destination)])
        return tuple(values)

    @staticmethod
    def _require_data(value: object) -> bytes:
        if not isinstance(value, bytes):  # pragma: no cover - request binding invariant
            raise RuntimeError("bound filesystem data is not bytes")
        return value

    @staticmethod
    def _category_for_error(error: Exception) -> FilesystemResultCategory:
        if isinstance(error, TargetValidationError):
            return FilesystemResultCategory.FAIL_CLOSED
        if isinstance(error, FilesystemPrimitiveError) and error.effect_possible:
            return FilesystemResultCategory.FAIL_INDETERMINATE
        if isinstance(error, FilesystemToolError | FilesystemPrimitiveError):
            return FilesystemResultCategory.TOOL_ERROR
        if bool(getattr(error, "effect_possible", False)):
            return FilesystemResultCategory.FAIL_INDETERMINATE
        return FilesystemResultCategory.FAIL_INDETERMINATE


def filesystem_base_metadata(
    *,
    requested_resource: str,
    canonical_resource: str,
    canonical_destination: str | None,
    argument_reference: str,
    policy_reference: str,
) -> dict[str, object]:
    return {
        "filesystem_audit_envelope_version": FILESYSTEM_AUDIT_ENVELOPE_VERSION,
        "filesystem_adapter_version": FILESYSTEM_ADAPTER_VERSION,
        "filesystem_canonicalization_version": FILESYSTEM_CANONICALIZATION_VERSION,
        "state_digest_version": STATE_DIGEST_VERSION,
        "requested_resource": requested_resource,
        "canonical_resource": canonical_resource,
        "canonical_destination": canonical_destination,
        "arguments_digest": argument_reference,
        "policy_reference": policy_reference,
    }


def _logical_parent(resource: str) -> str:
    if resource == LOGICAL_ROOT:  # pragma: no cover - mutating root rejected earlier
        return LOGICAL_ROOT
    parent = resource.rsplit("/", 1)[0]
    return parent or LOGICAL_ROOT


_MUTATING_OPERATIONS = frozenset(
    {
        FilesystemOperation.WRITE,
        FilesystemOperation.APPEND,
        FilesystemOperation.CREATE,
        FilesystemOperation.DELETE,
        FilesystemOperation.RENAME,
        FilesystemOperation.MKDIR,
    }
)
