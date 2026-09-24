"""FMED-L1 real-filesystem adapter with authorize-before-effect ordering."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import cast

from safetybox.audit import AuditRecorder, InMemoryAuditSink
from safetybox.authorization import CompoundAuthorizer
from safetybox.events import EventType
from safetybox.exceptions import AuditFailure, AuthorizationFailure
from safetybox.filesystem.audit import (
    FilesystemAuditBridge,
    FilesystemExecutionBoundary,
    arguments_digest,
    filesystem_base_metadata,
    governed_requested_identifier,
)
from safetybox.filesystem.canonicalization import canonicalize_logical_path
from safetybox.filesystem.errors import (
    CanonicalizationError,
    FilesystemMediationError,
    FilesystemPrimitiveError,
    FilesystemToolError,
    TargetValidationError,
)
from safetybox.filesystem.mapping import LogicalHostMapper
from safetybox.filesystem.models import (
    AuthorizationEvidence,
    FilesystemAuditEnvelope,
    FilesystemRequest,
    FilesystemResult,
    FilesystemResultCategory,
    FilesystemValue,
    PhysicalValidationStatus,
)
from safetybox.filesystem.primitives import RealFilesystemPrimitives
from safetybox.filesystem.versions import (
    FILESYSTEM_ADAPTER_VERSION,
    FILESYSTEM_AUDIT_ENVELOPE_VERSION,
    FILESYSTEM_CANONICALIZATION_VERSION,
    STATE_DIGEST_VERSION,
)
from safetybox.models import ActionRequest, Decision, EnforcementResult, PolicyDecision
from safetybox.monitor import ReferenceMonitor
from safetybox.protocols import Authorizer


@dataclass(slots=True)
class _DecisionCapturingAuthorizer:
    delegate: Authorizer
    decision: PolicyDecision | None = field(default=None, init=False)

    def authorize(self, request: ActionRequest) -> PolicyDecision:
        self.decision = self.delegate.authorize(request)
        return self.decision


@dataclass(slots=True)
class FilesystemAdapter:
    """Mediate typed requests below an explicit host root at FMED-L1.

    Physical validation uses lstat followed by ordinary pathname primitives.
    This is intentionally not race-safe confinement: name-to-object TOCTOU
    remains unsolved and direct filesystem routes bypass this adapter.
    """

    mapper: LogicalHostMapper
    authorizer: Authorizer
    policy_reference: str
    audit_recorder: AuditRecorder
    primitives: RealFilesystemPrimitives

    def __init__(
        self,
        *,
        mapper: LogicalHostMapper,
        authorizer: Authorizer,
        policy_reference: str,
        audit_recorder: AuditRecorder | None = None,
        primitives: RealFilesystemPrimitives | None = None,
    ) -> None:
        if not policy_reference:
            raise ValueError("policy_reference must not be empty")
        self.mapper = mapper
        self.authorizer = authorizer
        self.policy_reference = policy_reference
        self.audit_recorder = (
            AuditRecorder(InMemoryAuditSink()) if audit_recorder is None else audit_recorder
        )
        self.primitives = RealFilesystemPrimitives() if primitives is None else primitives

    def execute(self, request: FilesystemRequest) -> FilesystemResult:
        start_sequence = self.audit_recorder.last_sequence_number(request.session_id)
        requested_identifier = governed_requested_identifier(request.resource)
        ingress_request = ActionRequest(
            request.request_id,
            request.session_id,
            request.task_id,
            request.actor,
            request.operation.value,
            requested_identifier,
        )
        bridge = FilesystemAuditBridge(self.audit_recorder)
        ingress_metadata = self._precanonical_metadata(requested_identifier)
        try:
            ingress = bridge.emit(
                ingress_request,
                EventType.ADAPTER_REQUEST_RECEIVED,
                parent_event_id=None,
                metadata=ingress_metadata,
            )
            canonical_started = bridge.emit(
                ingress_request,
                EventType.CANONICALIZATION_STARTED,
                parent_event_id=ingress.event_id,
                metadata=ingress_metadata,
            )
        except AuditFailure:
            return self._failure_result(
                request,
                requested_identifier,
                None,
                None,
                None,
                FilesystemResultCategory.FAIL_CLOSED,
                "FS-AUDIT-PRE-EXECUTION",
                "Required audit evidence could not be committed before execution.",
                (),
                PhysicalValidationStatus.NOT_ATTEMPTED,
                False,
                False,
                None,
                None,
                start_sequence,
            )

        try:
            canonical_resource = canonicalize_logical_path(request.resource)
            canonical_destination = (
                canonicalize_logical_path(request.destination)
                if request.destination is not None
                else None
            )
        except Exception as error:
            canonical_error = (
                error
                if isinstance(error, CanonicalizationError)
                else CanonicalizationError(
                    "FS-CANONICALIZATION-FAILED",
                    "Logical path canonicalization could not complete safely.",
                    cause=error,
                )
            )
            try:
                bridge.emit(
                    ingress_request,
                    EventType.CANONICALIZATION_FAILED,
                    parent_event_id=canonical_started.event_id,
                    metadata={
                        **ingress_metadata,
                        "error_code": canonical_error.code,
                        "result_category": FilesystemResultCategory.FAIL_CLOSED.value,
                    },
                )
            except AuditFailure as audit_error:
                # The canonicalization failure remains fail-closed even when its
                # own evidence cannot be committed; no primitive is reachable.
                del audit_error
            return self._failure_result(
                request,
                requested_identifier,
                None,
                None,
                None,
                FilesystemResultCategory.FAIL_CLOSED,
                canonical_error.code,
                canonical_error.safe_message,
                (),
                PhysicalValidationStatus.NOT_ATTEMPTED,
                False,
                False,
                None,
                None,
                start_sequence,
            )

        argument_reference = arguments_digest(
            request.operation,
            canonical_resource,
            canonical_destination,
            request.data,
        )
        base_metadata = filesystem_base_metadata(
            requested_resource=requested_identifier,
            canonical_resource=canonical_resource,
            canonical_destination=canonical_destination,
            argument_reference=argument_reference,
            policy_reference=self.policy_reference,
        )
        action_request = ActionRequest(
            request.request_id,
            request.session_id,
            request.task_id,
            request.actor,
            request.operation.value,
            canonical_resource,
            {
                "destination": canonical_destination,
                "data": request.data,
                "arguments_digest": argument_reference,
            },
        )
        try:
            canonical_event = bridge.emit(
                action_request,
                EventType.CANONICALIZATION_SUCCEEDED,
                parent_event_id=canonical_started.event_id,
                metadata=base_metadata,
            )
        except AuditFailure:
            return self._failure_result(
                request,
                requested_identifier,
                canonical_resource,
                canonical_destination,
                argument_reference,
                FilesystemResultCategory.FAIL_CLOSED,
                "FS-AUDIT-PRE-EXECUTION",
                "Required audit evidence could not be committed before execution.",
                (),
                PhysicalValidationStatus.NOT_ATTEMPTED,
                False,
                False,
                None,
                None,
                start_sequence,
            )

        boundary = FilesystemExecutionBoundary(
            request.operation,
            self.mapper,
            self.primitives,
            bridge,
            canonical_destination,
            base_metadata,
        )
        selected_authorizer: Authorizer = self.authorizer
        if canonical_destination is not None:
            selected_authorizer = CompoundAuthorizer(self.authorizer, (canonical_destination,))
        capturing_authorizer = _DecisionCapturingAuthorizer(selected_authorizer)
        monitor = ReferenceMonitor(
            capturing_authorizer,
            boundary,
            self.audit_recorder,
            boundary,
        )
        enforcement: EnforcementResult | None = None
        try:
            enforcement = monitor.execute(
                action_request,
                parent_event_id=canonical_event.event_id,
                lifecycle_metadata=base_metadata,
            )
            authorizations = self._authorizations(enforcement.policy_decision, canonical_resource)
            if not enforcement.executed:
                return self._failure_result(
                    request,
                    requested_identifier,
                    canonical_resource,
                    canonical_destination,
                    argument_reference,
                    FilesystemResultCategory.DENY,
                    enforcement.policy_decision.rule_id,
                    "The filesystem request was denied by policy.",
                    authorizations,
                    PhysicalValidationStatus.NOT_ATTEMPTED,
                    False,
                    False,
                    None,
                    None,
                    start_sequence,
                    decision=Decision.DENY,
                )
            return self._success_result(
                request,
                requested_identifier,
                canonical_resource,
                canonical_destination,
                argument_reference,
                enforcement,
                boundary,
                start_sequence,
            )
        except AuthorizationFailure as error:
            return self._failure_result(
                request,
                requested_identifier,
                canonical_resource,
                canonical_destination,
                argument_reference,
                FilesystemResultCategory.FAIL_CLOSED,
                "FS-AUTHORIZATION-FAILED",
                "Authorization could not complete; no filesystem primitive was invoked.",
                self._failed_authorizations(error),
                PhysicalValidationStatus.NOT_ATTEMPTED,
                False,
                False,
                None,
                None,
                start_sequence,
            )
        except AuditFailure as error:
            category = (
                FilesystemResultCategory.FAIL_INDETERMINATE
                if error.execution_may_have_started
                else FilesystemResultCategory.FAIL_CLOSED
            )
            return self._failure_result(
                request,
                requested_identifier,
                canonical_resource,
                canonical_destination,
                argument_reference,
                category,
                "FS-AUDIT-POST-EXECUTION"
                if error.execution_may_have_started
                else "FS-AUDIT-PRE-EXECUTION",
                "Required audit evidence could not be committed.",
                self._captured_authorizations(capturing_authorizer, canonical_resource),
                boundary.validation_status,
                boundary.primitive_started,
                None,
                boundary.pre_state_digest,
                boundary.post_state_digest,
                start_sequence,
                decision=(
                    Decision.ALLOW
                    if boundary.validation_status is not PhysicalValidationStatus.NOT_ATTEMPTED
                    else None
                ),
            )
        except TargetValidationError as error:
            return self._error_from_mediation(
                request,
                requested_identifier,
                canonical_resource,
                canonical_destination,
                argument_reference,
                error,
                FilesystemResultCategory.FAIL_CLOSED,
                boundary,
                start_sequence,
                capturing_authorizer,
            )
        except (FilesystemToolError, FilesystemPrimitiveError) as error:
            category = (
                FilesystemResultCategory.FAIL_INDETERMINATE
                if error.effect_possible
                else FilesystemResultCategory.TOOL_ERROR
            )
            return self._error_from_mediation(
                request,
                requested_identifier,
                canonical_resource,
                canonical_destination,
                argument_reference,
                error,
                category,
                boundary,
                start_sequence,
                capturing_authorizer,
            )
        except Exception:
            category = (
                FilesystemResultCategory.FAIL_INDETERMINATE
                if boundary.primitive_started
                else FilesystemResultCategory.FAIL_CLOSED
            )
            return self._failure_result(
                request,
                requested_identifier,
                canonical_resource,
                canonical_destination,
                argument_reference,
                category,
                "FS-UNEXPECTED-FAILURE",
                "The filesystem request failed at a protected lifecycle boundary.",
                self._captured_authorizations(capturing_authorizer, canonical_resource),
                boundary.validation_status,
                boundary.primitive_started,
                None,
                boundary.pre_state_digest,
                boundary.post_state_digest,
                start_sequence,
                decision=(
                    Decision.ALLOW
                    if boundary.validation_status is not PhysicalValidationStatus.NOT_ATTEMPTED
                    else None
                ),
            )

    def _success_result(
        self,
        request: FilesystemRequest,
        requested_identifier: str,
        canonical_resource: str,
        canonical_destination: str | None,
        argument_reference: str,
        enforcement: EnforcementResult,
        boundary: FilesystemExecutionBoundary,
        start_sequence: int,
    ) -> FilesystemResult:
        authorizations = self._authorizations(enforcement.policy_decision, canonical_resource)
        evidence = self._envelope(
            request,
            requested_identifier,
            canonical_resource,
            canonical_destination,
            argument_reference,
            authorizations,
            boundary.validation_status,
            True,
            True,
            FilesystemResultCategory.ALLOW,
            None,
            boundary.pre_state_digest,
            boundary.post_state_digest,
            start_sequence,
        )
        value = enforcement.tool_result
        return FilesystemResult(
            request.request_id,
            FilesystemResultCategory.ALLOW,
            Decision.ALLOW,
            canonical_resource,
            canonical_destination,
            cast(FilesystemValue, value) if self._is_public_value(value) else None,
            None,
            None,
            evidence,
        )

    def _error_from_mediation(
        self,
        request: FilesystemRequest,
        requested_identifier: str,
        canonical_resource: str,
        canonical_destination: str | None,
        argument_reference: str,
        error: FilesystemMediationError,
        category: FilesystemResultCategory,
        boundary: FilesystemExecutionBoundary,
        start_sequence: int,
        capturing_authorizer: _DecisionCapturingAuthorizer,
    ) -> FilesystemResult:
        return self._failure_result(
            request,
            requested_identifier,
            canonical_resource,
            canonical_destination,
            argument_reference,
            category,
            error.code,
            error.safe_message,
            self._captured_authorizations(capturing_authorizer, canonical_resource),
            boundary.validation_status,
            boundary.primitive_started,
            False if not error.effect_possible else None,
            boundary.pre_state_digest,
            boundary.post_state_digest,
            start_sequence,
            decision=Decision.ALLOW,
        )

    def _failure_result(
        self,
        request: FilesystemRequest,
        requested_identifier: str,
        canonical_resource: str | None,
        canonical_destination: str | None,
        argument_reference: str | None,
        category: FilesystemResultCategory,
        error_code: str,
        error_message: str,
        authorizations: tuple[AuthorizationEvidence, ...],
        validation: PhysicalValidationStatus,
        attempted: bool,
        succeeded: bool | None,
        pre_digest: str | None,
        post_digest: str | None,
        start_sequence: int,
        *,
        decision: Decision | None = None,
    ) -> FilesystemResult:
        evidence = self._envelope(
            request,
            requested_identifier,
            canonical_resource,
            canonical_destination,
            argument_reference,
            authorizations,
            validation,
            attempted,
            succeeded,
            category,
            error_code,
            pre_digest,
            post_digest,
            start_sequence,
        )
        return FilesystemResult(
            request.request_id,
            category,
            decision,
            canonical_resource,
            canonical_destination,
            None,
            error_code,
            error_message,
            evidence,
        )

    def _envelope(
        self,
        request: FilesystemRequest,
        requested_identifier: str,
        canonical_resource: str | None,
        canonical_destination: str | None,
        argument_reference: str | None,
        authorizations: tuple[AuthorizationEvidence, ...],
        validation: PhysicalValidationStatus,
        attempted: bool,
        succeeded: bool | None,
        category: FilesystemResultCategory,
        error_code: str | None,
        pre_digest: str | None,
        post_digest: str | None,
        start_sequence: int,
    ) -> FilesystemAuditEnvelope:
        end = self.audit_recorder.last_sequence_number(request.session_id)
        return FilesystemAuditEnvelope(
            FILESYSTEM_AUDIT_ENVELOPE_VERSION,
            FILESYSTEM_ADAPTER_VERSION,
            FILESYSTEM_CANONICALIZATION_VERSION,
            STATE_DIGEST_VERSION,
            request.session_id,
            request.task_id,
            request.request_id,
            request.request_id,
            request.operation.value,
            requested_identifier,
            canonical_resource,
            canonical_destination,
            argument_reference,
            self.policy_reference,
            authorizations,
            validation,
            attempted,
            succeeded,
            category,
            error_code,
            pre_digest,
            post_digest,
            tuple(range(start_sequence + 1, end + 1)),
        )

    def _precanonical_metadata(self, requested_identifier: str) -> dict[str, object]:
        return {
            "filesystem_audit_envelope_version": FILESYSTEM_AUDIT_ENVELOPE_VERSION,
            "filesystem_adapter_version": FILESYSTEM_ADAPTER_VERSION,
            "filesystem_canonicalization_version": FILESYSTEM_CANONICALIZATION_VERSION,
            "state_digest_version": STATE_DIGEST_VERSION,
            "requested_resource": requested_identifier,
            "policy_reference": self.policy_reference,
        }

    @staticmethod
    def _authorizations(
        decision: PolicyDecision, primary_resource: str
    ) -> tuple[AuthorizationEvidence, ...]:
        records = decision.metadata.get("subdecisions")
        if isinstance(records, tuple):
            evidence: list[AuthorizationEvidence] = []
            for record in records:
                if not isinstance(record, dict):
                    record = dict(record)  # MappingProxy/Mapping after event freezing
                value = record.get("decision")
                if value in {Decision.ALLOW.value, Decision.DENY.value}:
                    evidence.append(
                        AuthorizationEvidence(
                            str(record["resource"]),
                            Decision(str(value)),
                            str(record["rule_id"]),
                        )
                    )
            return tuple(evidence)
        return (AuthorizationEvidence(primary_resource, decision.decision, decision.rule_id),)

    @classmethod
    def _captured_authorizations(
        cls, capture: _DecisionCapturingAuthorizer, primary_resource: str
    ) -> tuple[AuthorizationEvidence, ...]:
        if capture.decision is None:
            return ()
        return cls._authorizations(capture.decision, primary_resource)

    @staticmethod
    def _failed_authorizations(
        error: AuthorizationFailure,
    ) -> tuple[AuthorizationEvidence, ...]:
        cause = error.__cause__
        metadata = getattr(cause, "audit_metadata", None)
        if not isinstance(metadata, Mapping):
            return ()
        records = metadata.get("subdecisions")
        if not isinstance(records, tuple):
            return ()
        evidence: list[AuthorizationEvidence] = []
        for record in records:
            if not isinstance(record, Mapping):
                continue
            value = record.get("decision")
            evidence.append(
                AuthorizationEvidence(
                    str(record.get("resource", "")),
                    Decision(str(value)) if value in {"ALLOW", "DENY"} else None,
                    str(record["rule_id"]) if "rule_id" in record else None,
                    str(record["error_type"]) if "error_type" in record else None,
                )
            )
        return tuple(evidence)

    @staticmethod
    def _is_public_value(value: object) -> bool:
        from safetybox.filesystem.models import FilesystemStat

        return value is None or isinstance(value, bytes | tuple | FilesystemStat)
