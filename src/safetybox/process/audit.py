"""Canonical M3 bridge and protected process execution boundary."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from safetybox.audit import AuditRecorder
from safetybox.events import EventType, SafetyBoxEvent
from safetybox.exceptions import AuditFailure
from safetybox.models import ActionRequest
from safetybox.process.errors import (
    ProcessMediationError,
    ProcessNonzeroExitError,
    ProcessSignalError,
    ProcessSpawnError,
    ProcessTimeoutError,
    ProcessValidationError,
)
from safetybox.process.models import (
    ProcessResultCategory,
    ProcessTerminalClass,
    ProcessValidationStatus,
)
from safetybox.process.primitive import ProcessObservation, RealProcessPrimitive
from safetybox.process.validation import ProcessTargetValidator, ValidatedProcessTargets


@dataclass(slots=True)
class ProcessAuditBridge:
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
                "Audit recording failed before protected process execution.",
                execution_may_have_started=False,
                failed_event_type=event_type.value,
            ) from error


@dataclass(slots=True)
class ProcessExecutionBoundary:
    """Validate only after compound allow, then invoke the one spawn primitive."""

    validator: ProcessTargetValidator
    primitive: RealProcessPrimitive
    audit_bridge: ProcessAuditBridge
    canonical_cwd: str
    argv: tuple[str, ...]
    timeout_ms: int
    base_metadata: Mapping[str, object]
    authorization_ready: Callable[[], bool]
    executable_validation: ProcessValidationStatus = field(
        default=ProcessValidationStatus.NOT_ATTEMPTED, init=False
    )
    cwd_validation: ProcessValidationStatus = field(
        default=ProcessValidationStatus.NOT_ATTEMPTED, init=False
    )
    validated: ValidatedProcessTargets | None = field(default=None, init=False)
    primitive_invoked: bool = field(default=False, init=False)
    observation: ProcessObservation | None = field(default=None, init=False)

    def before_execution(
        self,
        request: ActionRequest,
        *,
        correlation_id: str,
        parent_event_id: str,
    ) -> str:
        del correlation_id
        executable_started = self.audit_bridge.emit(
            request,
            EventType.TARGET_VALIDATION_STARTED,
            parent_event_id=parent_event_id,
            metadata={**self.base_metadata, "validation_component": "process.exec"},
        )
        try:
            self.validator.validate_executable(request.resource)
        except ProcessValidationError as error:
            self.executable_validation = ProcessValidationStatus.REJECTED
            self._emit_validation_failure(
                request, executable_started.event_id, error, "process.exec"
            )
            raise
        self.executable_validation = ProcessValidationStatus.SUCCEEDED
        executable_succeeded = self.audit_bridge.emit(
            request,
            EventType.TARGET_VALIDATION_SUCCEEDED,
            parent_event_id=executable_started.event_id,
            metadata={
                **self.base_metadata,
                "validation_component": "process.exec",
                "validation_status": self.executable_validation.value,
            },
        )

        cwd_started = self.audit_bridge.emit(
            request,
            EventType.TARGET_VALIDATION_STARTED,
            parent_event_id=executable_succeeded.event_id,
            metadata={**self.base_metadata, "validation_component": "process.cwd"},
        )
        try:
            host_cwd = self.validator.validate_cwd(self.canonical_cwd)
        except ProcessValidationError as error:
            self.cwd_validation = ProcessValidationStatus.REJECTED
            self._emit_validation_failure(request, cwd_started.event_id, error, "process.cwd")
            raise
        self.cwd_validation = ProcessValidationStatus.SUCCEEDED
        cwd_succeeded = self.audit_bridge.emit(
            request,
            EventType.TARGET_VALIDATION_SUCCEEDED,
            parent_event_id=cwd_started.event_id,
            metadata={
                **self.base_metadata,
                "validation_component": "process.cwd",
                "validation_status": self.cwd_validation.value,
            },
        )
        self.validated = ValidatedProcessTargets(request.resource, host_cwd)
        return cwd_succeeded.event_id

    def execute(self, request: ActionRequest) -> object:
        if self.validated is None:  # pragma: no cover - monitor ordering invariant
            raise RuntimeError("process execution reached without validation")
        if not self.authorization_ready():  # pragma: no cover - composition invariant
            raise RuntimeError("process execution reached without complete authorization")
        self.primitive_invoked = True
        try:
            self.observation = self.primitive.spawn_and_wait(
                executable=self.validated.executable,
                argv=self.argv,
                cwd=self.validated.cwd,
                timeout_ms=self.timeout_ms,
            )
        except ProcessMediationError as error:
            self.observation = error.observation
            raise
        observation = self.observation
        if observation.timed_out:
            raise ProcessTimeoutError(
                "PROC-TIMEOUT",
                "The direct child exceeded its timeout and was terminated.",
                observation=observation,
            )
        if observation.signal is not None:
            raise ProcessSignalError(
                "PROC-SIGNAL",
                "The direct child terminated by signal.",
                observation=observation,
            )
        if observation.exit_code != 0:
            raise ProcessNonzeroExitError(
                "PROC-NONZERO-EXIT",
                "The direct child exited with a nonzero status.",
                observation=observation,
            )
        return observation

    def after_execution_success(
        self, request: ActionRequest, result: object
    ) -> Mapping[str, object]:
        del request, result
        return self._terminal_metadata(
            ProcessResultCategory.ALLOW_SUCCESS,
            ProcessTerminalClass.PROCESS_EXIT_0,
            None,
        )

    def after_execution_failure(
        self, request: ActionRequest, error: Exception
    ) -> Mapping[str, object]:
        del request
        category, terminal = self._failure_classification(error)
        return self._terminal_metadata(category, terminal, getattr(error, "code", None))

    def _emit_validation_failure(
        self,
        request: ActionRequest,
        parent_event_id: str,
        error: ProcessValidationError,
        component: str,
    ) -> None:
        self.audit_bridge.emit(
            request,
            EventType.TARGET_VALIDATION_FAILED,
            parent_event_id=parent_event_id,
            metadata={
                **self.base_metadata,
                "validation_component": component,
                "validation_status": ProcessValidationStatus.REJECTED.value,
                "error_code": error.code,
                "result_category": ProcessResultCategory.TOOL_ERROR.value,
                "terminal_class": ProcessTerminalClass.VALIDATION_REJECT_NOT_SPAWNED.value,
                "effect_possible": False,
                "primitive_invoked": False,
                "child_created": False,
            },
        )

    def _terminal_metadata(
        self,
        category: ProcessResultCategory,
        terminal: ProcessTerminalClass,
        error_code: str | None,
    ) -> Mapping[str, object]:
        observation = self.observation
        return {
            "result_category": category.value,
            "terminal_class": terminal.value,
            "effect_possible": terminal
            not in {
                ProcessTerminalClass.SPAWN_ERROR_NOT_CREATED,
                ProcessTerminalClass.FAIL_CLOSED_NOT_SPAWNED,
                ProcessTerminalClass.VALIDATION_REJECT_NOT_SPAWNED,
            },
            "error_code": error_code,
            "primitive_invoked": self.primitive_invoked,
            "child_created": None if observation is None else observation.child_created,
            "child_token": None if observation is None else observation.child_token,
            "pid": None if observation is None else observation.pid,
            "exit_code": None if observation is None else observation.exit_code,
            "signal": None if observation is None else observation.signal,
            "timed_out": False if observation is None else observation.timed_out,
            "term_sent": False if observation is None else observation.term_sent,
            "kill_sent": False if observation is None else observation.kill_sent,
            "stdout": self._stream_metadata(
                None if observation is None else observation.stdout_metadata
            ),
            "stderr": self._stream_metadata(
                None if observation is None else observation.stderr_metadata
            ),
        }

    @staticmethod
    def _failure_classification(
        error: Exception,
    ) -> tuple[ProcessResultCategory, ProcessTerminalClass]:
        if isinstance(error, ProcessSpawnError):
            return ProcessResultCategory.TOOL_ERROR, ProcessTerminalClass.SPAWN_ERROR_NOT_CREATED
        if isinstance(error, ProcessTimeoutError):
            return (
                ProcessResultCategory.TOOL_ERROR,
                ProcessTerminalClass.PROCESS_TIMEOUT_EFFECT_POSSIBLE,
            )
        if isinstance(error, ProcessSignalError):
            return (
                ProcessResultCategory.TOOL_ERROR,
                ProcessTerminalClass.PROCESS_SIGNALED_EFFECT_POSSIBLE,
            )
        if isinstance(error, ProcessNonzeroExitError):
            return (
                ProcessResultCategory.TOOL_ERROR,
                ProcessTerminalClass.PROCESS_EXIT_NONZERO_EFFECT_POSSIBLE,
            )
        return (
            ProcessResultCategory.FAIL_INDETERMINATE,
            ProcessTerminalClass.FAIL_INDETERMINATE_EXECUTION_POSSIBLE,
        )

    @staticmethod
    def _stream_metadata(value: object) -> Mapping[str, object] | None:
        from safetybox.process.models import StreamMetadata

        if not isinstance(value, StreamMetadata):
            return None
        return {
            "byte_count": value.byte_count,
            "sha256": value.sha256,
            "truncated": value.truncated,
            "capture_status": value.capture_status.value,
        }
