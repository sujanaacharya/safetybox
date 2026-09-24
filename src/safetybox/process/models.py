"""Immutable PMED-L1 request, result, and evidence models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from safetybox.models import Decision


class ProcessResultCategory(StrEnum):
    ALLOW_SUCCESS = "ALLOW_SUCCESS"
    DENY = "DENY"
    FAIL_CLOSED = "FAIL_CLOSED"
    TOOL_ERROR = "TOOL_ERROR"
    FAIL_INDETERMINATE = "FAIL_INDETERMINATE"


class ProcessTerminalClass(StrEnum):
    POLICY_DENY_NOT_SPAWNED = "POLICY_DENY_NOT_SPAWNED"
    FAIL_CLOSED_NOT_SPAWNED = "FAIL_CLOSED_NOT_SPAWNED"
    VALIDATION_REJECT_NOT_SPAWNED = "VALIDATION_REJECT_NOT_SPAWNED"
    SPAWN_ERROR_NOT_CREATED = "SPAWN_ERROR_NOT_CREATED"
    PROCESS_EXIT_0 = "PROCESS_EXIT_0"
    PROCESS_EXIT_NONZERO_EFFECT_POSSIBLE = "PROCESS_EXIT_NONZERO_EFFECT_POSSIBLE"
    PROCESS_TIMEOUT_EFFECT_POSSIBLE = "PROCESS_TIMEOUT_EFFECT_POSSIBLE"
    PROCESS_SIGNALED_EFFECT_POSSIBLE = "PROCESS_SIGNALED_EFFECT_POSSIBLE"
    FAIL_INDETERMINATE_EXECUTION_POSSIBLE = "FAIL_INDETERMINATE_EXECUTION_POSSIBLE"


class ProcessValidationStatus(StrEnum):
    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    SUCCEEDED = "SUCCEEDED"
    REJECTED = "REJECTED"


class CaptureStatus(StrEnum):
    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class ProcessRequest:
    session_id: str
    task_id: str
    request_id: str
    actor: str
    executable: str
    argv: tuple[str, ...]
    logical_cwd: str
    timeout_ms: int

    def __post_init__(self) -> None:
        for name in ("session_id", "task_id", "request_id", "actor"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"{name} must be a non-empty string.")
        if not isinstance(self.argv, tuple):
            object.__setattr__(self, "argv", tuple(self.argv))


@dataclass(frozen=True, slots=True)
class ArgumentCommitment:
    index: int
    utf8_length: int
    sha256: str


@dataclass(frozen=True, slots=True)
class ProcessAuthorizationEvidence:
    component: str
    session_id: str
    task_id: str
    action: str
    resource: str
    decision: Decision | None
    rule_id: str | None
    reason: str | None
    authority_source: str
    contract_reference: str
    applicable_capability_action: str | None = None
    applicable_capability_resource: str | None = None
    error_type: str | None = None


@dataclass(frozen=True, slots=True)
class StreamMetadata:
    byte_count: int | None
    sha256: str | None
    truncated: bool
    capture_status: CaptureStatus


@dataclass(frozen=True, slots=True)
class ProcessAuditEnvelope:
    envelope_version: str
    adapter_version: str
    canonicalization_version: str
    primitive_version: str
    session_id: str
    task_id: str
    actor: str
    request_id: str
    correlation_id: str
    action: str
    requested_executable: str
    canonical_executable: str | None
    argv_count: int
    argv_commitments: tuple[ArgumentCommitment, ...]
    argv_tuple_digest: str | None
    requested_cwd: str
    canonical_cwd: str | None
    environment_profile: str
    timeout_ms: int
    policy_reference: str
    authorizations: tuple[ProcessAuthorizationEvidence, ...]
    executable_validation: ProcessValidationStatus
    cwd_validation: ProcessValidationStatus
    spawn_attempted: bool
    primitive_invoked: bool
    child_created: bool | None
    child_token: str | None
    pid: int | None
    exit_code: int | None
    signal: int | None
    timed_out: bool
    term_sent: bool
    kill_sent: bool
    stdout: StreamMetadata
    stderr: StreamMetadata
    terminal_class: ProcessTerminalClass
    result_category: ProcessResultCategory
    effect_possible: bool
    error_code: str | None
    sequence_numbers: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ProcessResult:
    request_id: str
    category: ProcessResultCategory
    terminal_class: ProcessTerminalClass
    decision: Decision | None
    canonical_executable: str | None
    canonical_cwd: str | None
    stdout: bytes | None
    stderr: bytes | None
    exit_code: int | None
    signal: int | None
    timed_out: bool
    error_code: str | None
    error_message: str | None
    evidence: ProcessAuditEnvelope

    @property
    def succeeded(self) -> bool:
        return self.category is ProcessResultCategory.ALLOW_SUCCESS
