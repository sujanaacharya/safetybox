"""PMED-L1 direct-child process adapter."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field

from safetybox.audit import AuditRecorder, InMemoryAuditSink
from safetybox.authorization import AuthorizationComponent, CompoundActionAuthorizer
from safetybox.events import EventType
from safetybox.exceptions import AuditFailure, AuthorizationFailure
from safetybox.filesystem.mapping import LogicalHostMapper
from safetybox.models import ActionRequest, Decision, PolicyDecision
from safetybox.monitor import ReferenceMonitor
from safetybox.policy import TaskContractPolicy
from safetybox.process.audit import ProcessAuditBridge, ProcessExecutionBoundary
from safetybox.process.canonicalization import (
    canonicalize_executable,
    canonicalize_process_cwd,
    commit_argv,
    validate_timeout,
)
from safetybox.process.errors import (
    ProcessCanonicalizationError,
    ProcessMediationError,
    ProcessNonzeroExitError,
    ProcessSignalError,
    ProcessSpawnError,
    ProcessTimeoutError,
    ProcessValidationError,
)
from safetybox.process.models import (
    ArgumentCommitment,
    CaptureStatus,
    ProcessAuditEnvelope,
    ProcessAuthorizationEvidence,
    ProcessRequest,
    ProcessResult,
    ProcessResultCategory,
    ProcessTerminalClass,
    ProcessValidationStatus,
    StreamMetadata,
)
from safetybox.process.primitive import ProcessObservation, RealProcessPrimitive
from safetybox.process.validation import ProcessTargetValidator
from safetybox.process.versions import (
    PROCESS_ADAPTER_VERSION,
    PROCESS_AUDIT_ENVELOPE_VERSION,
    PROCESS_CANONICALIZATION_VERSION,
    PROCESS_ENVIRONMENT_PROFILE,
    PROCESS_PRIMITIVE_VERSION,
)


@dataclass(slots=True)
class _DecisionCapturingAuthorizer:
    delegate: CompoundActionAuthorizer
    decision: PolicyDecision | None = field(default=None, init=False)

    def authorize(self, request: ActionRequest) -> PolicyDecision:
        self.decision = self.delegate.authorize(request)
        if self.decision.decision is Decision.DENY:
            self.decision = PolicyDecision(
                self.decision.decision,
                self.decision.rule_id,
                self.decision.reason,
                {
                    **dict(self.decision.metadata),
                    "terminal_class": ProcessTerminalClass.POLICY_DENY_NOT_SPAWNED.value,
                    "effect_possible": False,
                },
            )
        return self.decision

    def all_allowed(self) -> bool:
        if self.decision is None or self.decision.decision is not Decision.ALLOW:
            return False
        records = self.decision.metadata.get("subdecisions")
        return (
            isinstance(records, tuple)
            and len(records) == 2
            and all(
                isinstance(record, Mapping) and record.get("decision") == Decision.ALLOW.value
                for record in records
            )
        )


@dataclass(slots=True)
class ProcessAdapter:
    """Authorize, validate, audit, and directly execute one native child.

    Path validation followed by ``Popen`` is intentionally not TOCTOU-safe.
    Only the direct child is observed; descendants and child syscalls are not
    confined by PMED-L1.
    """

    mapper: LogicalHostMapper
    authorizer: TaskContractPolicy
    policy_reference: str
    audit_recorder: AuditRecorder
    primitive: RealProcessPrimitive

    def __init__(
        self,
        *,
        mapper: LogicalHostMapper,
        authorizer: TaskContractPolicy,
        policy_reference: str,
        audit_recorder: AuditRecorder | None = None,
        primitive: RealProcessPrimitive | None = None,
    ) -> None:
        if not policy_reference:
            raise ValueError("policy_reference must not be empty")
        if not isinstance(authorizer, TaskContractPolicy):
            raise TypeError("ProcessAdapter requires the authoritative TaskContractPolicy path.")
        self.mapper = mapper
        self.authorizer = authorizer
        self.policy_reference = policy_reference
        self.audit_recorder = (
            AuditRecorder(InMemoryAuditSink()) if audit_recorder is None else audit_recorder
        )
        self.primitive = RealProcessPrimitive() if primitive is None else primitive

    def execute(self, request: ProcessRequest) -> ProcessResult:
        start_sequence = self.audit_recorder.last_sequence_number(request.session_id)
        requested_executable = self._governed_identifier(request.executable)
        requested_cwd = self._governed_identifier(request.logical_cwd)
        ingress_request = ActionRequest(
            request.request_id,
            request.session_id,
            request.task_id,
            request.actor,
            "process.exec",
            requested_executable,
        )
        bridge = ProcessAuditBridge(self.audit_recorder)
        precanonical = self._precanonical_metadata(requested_executable, requested_cwd, request)
        try:
            ingress = bridge.emit(
                ingress_request,
                EventType.ADAPTER_REQUEST_RECEIVED,
                parent_event_id=None,
                metadata=precanonical,
            )
            canonical_started = bridge.emit(
                ingress_request,
                EventType.CANONICALIZATION_STARTED,
                parent_event_id=ingress.event_id,
                metadata=precanonical,
            )
        except AuditFailure:
            return self._result(
                request,
                requested_executable,
                requested_cwd,
                None,
                None,
                (),
                None,
                (),
                ProcessResultCategory.FAIL_CLOSED,
                ProcessTerminalClass.FAIL_CLOSED_NOT_SPAWNED,
                "PROC-AUDIT-PRE-EXECUTION",
                "Required audit evidence could not be committed before execution.",
                None,
                None,
                start_sequence,
            )

        try:
            canonical_executable = canonicalize_executable(request.executable)
            canonical_cwd = canonicalize_process_cwd(request.logical_cwd)
            commitments, tuple_digest = commit_argv(request.argv)
            validate_timeout(request.timeout_ms)
        except Exception as error:
            canonical_error = (
                error
                if isinstance(error, ProcessCanonicalizationError)
                else ProcessCanonicalizationError(
                    "PROC-CANONICALIZATION-FAILED",
                    "Process request canonicalization could not complete safely.",
                    cause=error,
                )
            )
            try:
                bridge.emit(
                    ingress_request,
                    EventType.CANONICALIZATION_FAILED,
                    parent_event_id=canonical_started.event_id,
                    metadata={
                        **precanonical,
                        "error_code": canonical_error.code,
                        "result_category": ProcessResultCategory.FAIL_CLOSED.value,
                        "terminal_class": ProcessTerminalClass.FAIL_CLOSED_NOT_SPAWNED.value,
                        "effect_possible": False,
                    },
                )
            except AuditFailure:
                pass
            return self._result(
                request,
                requested_executable,
                requested_cwd,
                None,
                None,
                (),
                None,
                (),
                ProcessResultCategory.FAIL_CLOSED,
                ProcessTerminalClass.FAIL_CLOSED_NOT_SPAWNED,
                canonical_error.code,
                canonical_error.safe_message,
                None,
                None,
                start_sequence,
            )

        base_metadata = self._base_metadata(
            requested_executable,
            canonical_executable,
            requested_cwd,
            canonical_cwd,
            commitments,
            tuple_digest,
            request.timeout_ms,
        )
        action_request = ActionRequest(
            request.request_id,
            request.session_id,
            request.task_id,
            request.actor,
            "process.exec",
            canonical_executable,
            {"argv_tuple_digest": tuple_digest, "timeout_ms": request.timeout_ms},
        )
        cwd_request = ActionRequest(
            request.request_id,
            request.session_id,
            request.task_id,
            request.actor,
            "process.cwd",
            canonical_cwd,
            {"argv_tuple_digest": tuple_digest, "timeout_ms": request.timeout_ms},
        )
        try:
            canonical_event = bridge.emit(
                action_request,
                EventType.CANONICALIZATION_SUCCEEDED,
                parent_event_id=canonical_started.event_id,
                metadata=base_metadata,
            )
        except AuditFailure:
            return self._result(
                request,
                requested_executable,
                requested_cwd,
                canonical_executable,
                canonical_cwd,
                commitments,
                tuple_digest,
                (),
                ProcessResultCategory.FAIL_CLOSED,
                ProcessTerminalClass.FAIL_CLOSED_NOT_SPAWNED,
                "PROC-AUDIT-PRE-EXECUTION",
                "Required audit evidence could not be committed before execution.",
                None,
                None,
                start_sequence,
            )

        compound = CompoundActionAuthorizer(
            self.authorizer,
            (AuthorizationComponent("process.cwd", cwd_request),),
            primary_name="process.exec",
        )
        capture = _DecisionCapturingAuthorizer(compound)
        boundary = ProcessExecutionBoundary(
            ProcessTargetValidator(self.mapper),
            self.primitive,
            bridge,
            canonical_cwd,
            request.argv,
            request.timeout_ms,
            base_metadata,
            capture.all_allowed,
        )
        monitor = ReferenceMonitor(capture, boundary, self.audit_recorder, boundary)
        try:
            enforcement = monitor.execute(
                action_request,
                parent_event_id=canonical_event.event_id,
                lifecycle_metadata=base_metadata,
            )
            authorizations = self._authorizations(enforcement.policy_decision)
            if not enforcement.executed:
                return self._result(
                    request,
                    requested_executable,
                    requested_cwd,
                    canonical_executable,
                    canonical_cwd,
                    commitments,
                    tuple_digest,
                    authorizations,
                    ProcessResultCategory.DENY,
                    ProcessTerminalClass.POLICY_DENY_NOT_SPAWNED,
                    enforcement.policy_decision.rule_id,
                    "The process request was denied by policy.",
                    Decision.DENY,
                    None,
                    start_sequence,
                    boundary,
                )
            observation = enforcement.tool_result
            if not isinstance(observation, ProcessObservation):  # pragma: no cover
                raise RuntimeError("process primitive returned an invalid observation")
            return self._result(
                request,
                requested_executable,
                requested_cwd,
                canonical_executable,
                canonical_cwd,
                commitments,
                tuple_digest,
                authorizations,
                ProcessResultCategory.ALLOW_SUCCESS,
                ProcessTerminalClass.PROCESS_EXIT_0,
                None,
                None,
                Decision.ALLOW,
                observation,
                start_sequence,
                boundary,
            )
        except AuthorizationFailure as error:
            return self._result(
                request,
                requested_executable,
                requested_cwd,
                canonical_executable,
                canonical_cwd,
                commitments,
                tuple_digest,
                self._failed_authorizations(error),
                ProcessResultCategory.FAIL_CLOSED,
                ProcessTerminalClass.FAIL_CLOSED_NOT_SPAWNED,
                "PROC-AUTHORIZATION-FAILED",
                "Authorization could not complete; no process was spawned.",
                None,
                None,
                start_sequence,
                boundary,
            )
        except AuditFailure as error:
            post_spawn = error.execution_may_have_started or bool(
                boundary.observation and boundary.observation.child_created
            )
            return self._result(
                request,
                requested_executable,
                requested_cwd,
                canonical_executable,
                canonical_cwd,
                commitments,
                tuple_digest,
                self._captured_authorizations(capture),
                ProcessResultCategory.FAIL_INDETERMINATE
                if post_spawn
                else ProcessResultCategory.FAIL_CLOSED,
                ProcessTerminalClass.FAIL_INDETERMINATE_EXECUTION_POSSIBLE
                if post_spawn
                else ProcessTerminalClass.FAIL_CLOSED_NOT_SPAWNED,
                "PROC-AUDIT-POST-SPAWN" if post_spawn else "PROC-AUDIT-PRE-EXECUTION",
                "Required process audit evidence could not be committed.",
                None if capture.decision is None else capture.decision.decision,
                boundary.observation,
                start_sequence,
                boundary,
            )
        except ProcessValidationError as error:
            return self._result(
                request,
                requested_executable,
                requested_cwd,
                canonical_executable,
                canonical_cwd,
                commitments,
                tuple_digest,
                self._captured_authorizations(capture),
                ProcessResultCategory.TOOL_ERROR,
                ProcessTerminalClass.VALIDATION_REJECT_NOT_SPAWNED,
                error.code,
                error.safe_message,
                Decision.ALLOW,
                None,
                start_sequence,
                boundary,
            )
        except ProcessMediationError as error:
            category, terminal = self._classify_error(error)
            return self._result(
                request,
                requested_executable,
                requested_cwd,
                canonical_executable,
                canonical_cwd,
                commitments,
                tuple_digest,
                self._captured_authorizations(capture),
                category,
                terminal,
                error.code,
                error.safe_message,
                Decision.ALLOW,
                error.observation,
                start_sequence,
                boundary,
            )
        except Exception:
            post_spawn = boundary.primitive_invoked
            return self._result(
                request,
                requested_executable,
                requested_cwd,
                canonical_executable,
                canonical_cwd,
                commitments,
                tuple_digest,
                self._captured_authorizations(capture),
                ProcessResultCategory.FAIL_INDETERMINATE
                if post_spawn
                else ProcessResultCategory.FAIL_CLOSED,
                ProcessTerminalClass.FAIL_INDETERMINATE_EXECUTION_POSSIBLE
                if post_spawn
                else ProcessTerminalClass.FAIL_CLOSED_NOT_SPAWNED,
                "PROC-UNEXPECTED-FAILURE",
                "The process request failed at a protected lifecycle boundary.",
                None if capture.decision is None else capture.decision.decision,
                boundary.observation,
                start_sequence,
                boundary,
            )

    @staticmethod
    def _classify_error(
        error: ProcessMediationError,
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

    def _result(
        self,
        request: ProcessRequest,
        requested_executable: str,
        requested_cwd: str,
        canonical_executable: str | None,
        canonical_cwd: str | None,
        commitments: tuple[ArgumentCommitment, ...],
        tuple_digest: str | None,
        authorizations: tuple[ProcessAuthorizationEvidence, ...],
        category: ProcessResultCategory,
        terminal: ProcessTerminalClass,
        error_code: str | None,
        error_message: str | None,
        decision: Decision | None,
        observation: ProcessObservation | None,
        start_sequence: int,
        boundary: ProcessExecutionBoundary | None = None,
    ) -> ProcessResult:
        empty = StreamMetadata(None, None, False, CaptureStatus.NOT_ATTEMPTED)
        stdout_metadata = empty if observation is None else observation.stdout_metadata
        stderr_metadata = empty if observation is None else observation.stderr_metadata
        end_sequence = self.audit_recorder.last_sequence_number(request.session_id)
        envelope = ProcessAuditEnvelope(
            PROCESS_AUDIT_ENVELOPE_VERSION,
            PROCESS_ADAPTER_VERSION,
            PROCESS_CANONICALIZATION_VERSION,
            PROCESS_PRIMITIVE_VERSION,
            request.session_id,
            request.task_id,
            request.actor,
            request.request_id,
            request.request_id,
            "process.exec",
            requested_executable,
            canonical_executable,
            len(request.argv),
            commitments,
            tuple_digest,
            requested_cwd,
            canonical_cwd,
            PROCESS_ENVIRONMENT_PROFILE,
            request.timeout_ms,
            self.policy_reference,
            authorizations,
            ProcessValidationStatus.NOT_ATTEMPTED
            if boundary is None
            else boundary.executable_validation,
            ProcessValidationStatus.NOT_ATTEMPTED if boundary is None else boundary.cwd_validation,
            False if boundary is None else boundary.primitive_invoked,
            False if boundary is None else boundary.primitive_invoked,
            False
            if observation is None and (boundary is None or not boundary.primitive_invoked)
            else (None if observation is None else observation.child_created),
            None if observation is None else observation.child_token,
            None if observation is None else observation.pid,
            None if observation is None else observation.exit_code,
            None if observation is None else observation.signal,
            False if observation is None else observation.timed_out,
            False if observation is None else observation.term_sent,
            False if observation is None else observation.kill_sent,
            stdout_metadata,
            stderr_metadata,
            terminal,
            category,
            terminal
            in {
                ProcessTerminalClass.PROCESS_EXIT_0,
                ProcessTerminalClass.PROCESS_EXIT_NONZERO_EFFECT_POSSIBLE,
                ProcessTerminalClass.PROCESS_TIMEOUT_EFFECT_POSSIBLE,
                ProcessTerminalClass.PROCESS_SIGNALED_EFFECT_POSSIBLE,
                ProcessTerminalClass.FAIL_INDETERMINATE_EXECUTION_POSSIBLE,
            },
            error_code,
            tuple(range(start_sequence + 1, end_sequence + 1)),
        )
        return ProcessResult(
            request.request_id,
            category,
            terminal,
            decision,
            canonical_executable,
            canonical_cwd,
            None if observation is None else observation.stdout,
            None if observation is None else observation.stderr,
            None if observation is None else observation.exit_code,
            None if observation is None else observation.signal,
            False if observation is None else observation.timed_out,
            error_code,
            error_message,
            envelope,
        )

    def _precanonical_metadata(
        self, executable: str, cwd: str, request: ProcessRequest
    ) -> dict[str, object]:
        return {
            "process_audit_envelope_version": PROCESS_AUDIT_ENVELOPE_VERSION,
            "process_adapter_version": PROCESS_ADAPTER_VERSION,
            "process_canonicalization_version": PROCESS_CANONICALIZATION_VERSION,
            "process_primitive_version": PROCESS_PRIMITIVE_VERSION,
            "requested_executable": executable,
            "requested_cwd": cwd,
            "argv_count": len(request.argv),
            "environment_profile": PROCESS_ENVIRONMENT_PROFILE,
            "timeout_ms": request.timeout_ms,
            "policy_reference": self.policy_reference,
        }

    def _base_metadata(
        self,
        requested_executable: str,
        canonical_executable: str,
        requested_cwd: str,
        canonical_cwd: str,
        commitments: tuple[ArgumentCommitment, ...],
        tuple_digest: str,
        timeout_ms: int,
    ) -> dict[str, object]:
        return {
            **self._precanonical_metadata_values(
                requested_executable, requested_cwd, len(commitments), timeout_ms
            ),
            "canonical_executable": canonical_executable,
            "canonical_cwd": canonical_cwd,
            "argv_commitments": tuple(
                {"index": item.index, "utf8_length": item.utf8_length, "sha256": item.sha256}
                for item in commitments
            ),
            "argv_tuple_digest": tuple_digest,
        }

    def _precanonical_metadata_values(
        self, executable: str, cwd: str, argv_count: int, timeout_ms: int
    ) -> dict[str, object]:
        return {
            "process_audit_envelope_version": PROCESS_AUDIT_ENVELOPE_VERSION,
            "process_adapter_version": PROCESS_ADAPTER_VERSION,
            "process_canonicalization_version": PROCESS_CANONICALIZATION_VERSION,
            "process_primitive_version": PROCESS_PRIMITIVE_VERSION,
            "requested_executable": executable,
            "requested_cwd": cwd,
            "argv_count": argv_count,
            "environment_profile": PROCESS_ENVIRONMENT_PROFILE,
            "timeout_ms": timeout_ms,
            "policy_reference": self.policy_reference,
        }

    def _authorizations(self, decision: PolicyDecision) -> tuple[ProcessAuthorizationEvidence, ...]:
        records = decision.metadata.get("subdecisions")
        if not isinstance(records, tuple):
            return ()
        values: list[ProcessAuthorizationEvidence] = []
        for record in records:
            if not isinstance(record, Mapping):
                continue
            capability = record.get("applicable_capability")
            capability_action: str | None = None
            capability_resource: str | None = None
            if isinstance(capability, Mapping):
                capability_action = str(capability.get("action"))
                capability_resource = str(capability.get("resource"))
            raw_decision = record.get("decision")
            values.append(
                ProcessAuthorizationEvidence(
                    str(record.get("component", "")),
                    str(record.get("session_id", "")),
                    str(record.get("task_id", "")),
                    str(record.get("action", "")),
                    str(record.get("resource", "")),
                    Decision(str(raw_decision)) if raw_decision in {"ALLOW", "DENY"} else None,
                    str(record["rule_id"]) if "rule_id" in record else None,
                    str(record["reason"]) if "reason" in record else None,
                    str(record.get("authority_source", "TaskContract")),
                    self.policy_reference,
                    capability_action,
                    capability_resource,
                    str(record["error_type"]) if "error_type" in record else None,
                )
            )
        return tuple(values)

    def _captured_authorizations(
        self, capture: _DecisionCapturingAuthorizer
    ) -> tuple[ProcessAuthorizationEvidence, ...]:
        return () if capture.decision is None else self._authorizations(capture.decision)

    def _failed_authorizations(
        self, error: AuthorizationFailure
    ) -> tuple[ProcessAuthorizationEvidence, ...]:
        cause = error.__cause__
        metadata = getattr(cause, "audit_metadata", None)
        if not isinstance(metadata, Mapping):
            return ()
        decision = PolicyDecision(
            Decision.DENY,
            "POL-COMPOUND-ERROR",
            "Compound authorization failed closed.",
            {"subdecisions": metadata.get("subdecisions", ())},
        )
        return self._authorizations(decision)

    @staticmethod
    def _governed_identifier(value: object) -> str:
        if isinstance(value, str) and "\x00" not in value:
            return value
        payload = f"{type(value).__name__}:{value!r}".encode("utf-8", errors="replace")
        return f"governed-sha256:{hashlib.sha256(payload).hexdigest()}"
