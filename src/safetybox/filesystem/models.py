"""Immutable request, result, and evidence models for filesystem mediation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TypeAlias

from safetybox.models import Decision


class FilesystemOperation(StrEnum):
    READ = "filesystem.read"
    WRITE = "filesystem.write"
    APPEND = "filesystem.append"
    CREATE = "filesystem.create"
    DELETE = "filesystem.delete"
    RENAME = "filesystem.rename"
    MKDIR = "filesystem.mkdir"
    LIST = "filesystem.list"
    STAT = "filesystem.stat"


class FilesystemResultCategory(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    FAIL_CLOSED = "FAIL_CLOSED"
    TOOL_ERROR = "TOOL_ERROR"
    FAIL_INDETERMINATE = "FAIL_INDETERMINATE"


class PhysicalValidationStatus(StrEnum):
    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    SUCCEEDED = "SUCCEEDED"
    REJECTED = "TARGET_VALIDATION_REJECT"


class FilesystemEntryType(StrEnum):
    FILE = "FILE"
    DIRECTORY = "DIRECTORY"


@dataclass(frozen=True, slots=True)
class FilesystemRequest:
    """One fully attributed, typed adapter request.

    ``data`` is valid only for write/append/create and is never copied into audit.
    ``destination`` is valid only for rename.
    """

    session_id: str
    task_id: str
    request_id: str
    actor: str
    operation: FilesystemOperation
    resource: str
    destination: str | None = None
    data: bytes | None = None

    def __post_init__(self) -> None:
        for name in ("session_id", "task_id", "request_id", "actor"):
            if not getattr(self, name):
                raise ValueError(f"{name} must not be empty.")
        data_operations = {
            FilesystemOperation.WRITE,
            FilesystemOperation.APPEND,
            FilesystemOperation.CREATE,
        }
        if self.operation in data_operations:
            if not isinstance(self.data, bytes):
                raise TypeError("write, append, and create require bytes data.")
        elif self.data is not None:
            raise ValueError("This filesystem operation does not accept data.")
        if self.operation is FilesystemOperation.RENAME:
            if not isinstance(self.destination, str):
                raise TypeError("rename requires a destination string.")
        elif self.destination is not None:
            raise ValueError("Only rename accepts a destination.")


@dataclass(frozen=True, slots=True)
class AuthorizationEvidence:
    resource: str
    decision: Decision | None
    rule_id: str | None
    error_type: str | None = None


@dataclass(frozen=True, slots=True)
class FilesystemStat:
    """Deliberately minimized, stable stat result."""

    entry_type: FilesystemEntryType
    size: int | None = None
    link_count: int | None = None


@dataclass(frozen=True, slots=True)
class StateDigest:
    version: str
    digest: str
    canonical_json: str


@dataclass(frozen=True, slots=True)
class FilesystemAuditEnvelope:
    """M3-compatible reconstruction view; raw file payloads are excluded."""

    envelope_version: str
    adapter_version: str
    canonicalization_version: str
    state_digest_version: str
    session_id: str
    task_id: str
    request_id: str
    correlation_id: str
    action: str
    requested_resource: str
    canonical_resource: str | None
    canonical_destination: str | None
    arguments_digest: str | None
    policy_reference: str
    authorizations: tuple[AuthorizationEvidence, ...]
    physical_validation: PhysicalValidationStatus
    execution_attempted: bool
    execution_succeeded: bool | None
    result_category: FilesystemResultCategory
    error_code: str | None
    pre_state_digest: str | None
    post_state_digest: str | None
    sequence_numbers: tuple[int, ...]


FilesystemValue: TypeAlias = bytes | tuple[str, ...] | FilesystemStat | None


@dataclass(frozen=True, slots=True)
class FilesystemResult:
    request_id: str
    category: FilesystemResultCategory
    decision: Decision | None
    canonical_resource: str | None
    canonical_destination: str | None
    value: FilesystemValue
    error_code: str | None
    error_message: str | None
    evidence: FilesystemAuditEnvelope

    @property
    def succeeded(self) -> bool:
        return self.category is FilesystemResultCategory.ALLOW
