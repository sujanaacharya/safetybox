"""The minimal deterministic reference monitor."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from safetybox.audit import AuditRecorder, InMemoryAuditSink
from safetybox.events import EventType, SafetyBoxEvent
from safetybox.exceptions import AuditFailure, AuthorizationFailure
from safetybox.models import ActionRequest, Decision, EnforcementResult
from safetybox.protocols import Authorizer, ExecutionLifecycleHook, ProtectedTool


@dataclass(frozen=True, slots=True)
class ReferenceMonitor:
    """Authorize every request before it can reach the protected tool.

    This API has one forwarding branch: an explicit ``ALLOW`` returned by the
    configured authorizer. A denial returns without calling the tool. An
    authorizer exception raises :class:`AuthorizationFailure` before any tool
    invocation, which is M1's fail-closed behavior.
    """

    authorizer: Authorizer
    protected_tool: ProtectedTool
    audit_recorder: AuditRecorder = field(
        default_factory=lambda: AuditRecorder(InMemoryAuditSink())
    )
    lifecycle_hook: ExecutionLifecycleHook | None = None

    def execute(
        self,
        request: ActionRequest,
        *,
        parent_event_id: str | None = None,
        lifecycle_metadata: Mapping[str, object] | None = None,
    ) -> EnforcementResult:
        """Authorize ``request`` and forward it only after an explicit allow."""
        recorder = self.audit_recorder
        correlation_id = request.request_id
        extended_lifecycle = (
            parent_event_id is not None
            or lifecycle_metadata is not None
            or self.lifecycle_hook is not None
        )
        base_metadata = {} if lifecycle_metadata is None else dict(lifecycle_metadata)
        parent_event = self._emit(
            recorder,
            request,
            EventType.ACTION_REQUESTED,
            correlation_id,
            parent_event_id,
            metadata=base_metadata,
        )
        parent_event = self._emit(
            recorder,
            request,
            EventType.AUTHORIZATION_STARTED,
            correlation_id,
            parent_event.event_id,
            metadata=base_metadata,
        )
        try:
            policy_decision = self.authorizer.authorize(request)
        except Exception as error:
            self._emit(
                recorder,
                request,
                EventType.AUTHORIZATION_FAILED,
                correlation_id,
                parent_event.event_id,
                metadata=(
                    self._merged_metadata(
                        base_metadata,
                        {
                            "error_type": type(error).__name__,
                            "result_category": "FAIL_CLOSED",
                            **self._safe_error_metadata(error),
                        },
                    )
                    if extended_lifecycle
                    else {"error_type": type(error).__name__}
                ),
            )
            message = "Authorization failed; protected action was not executed."
            raise AuthorizationFailure(message) from error

        if policy_decision.decision is Decision.DENY:
            self._emit(
                recorder,
                request,
                EventType.AUTHORIZATION_DENIED,
                correlation_id,
                parent_event.event_id,
                rule_id=policy_decision.rule_id,
                decision=policy_decision.decision,
                executed=False,
                metadata=(
                    self._merged_metadata(
                        base_metadata,
                        dict(policy_decision.metadata),
                        {
                            "execution_attempted": False,
                            "execution_succeeded": False,
                            "result_category": "DENY",
                        },
                    )
                    if extended_lifecycle
                    else None
                ),
            )
            return EnforcementResult(
                request=request,
                policy_decision=policy_decision,
                executed=False,
                correlation_id=correlation_id,
            )

        if policy_decision.decision is Decision.ALLOW:
            parent_event = self._emit(
                recorder,
                request,
                EventType.AUTHORIZATION_ALLOWED,
                correlation_id,
                parent_event.event_id,
                rule_id=policy_decision.rule_id,
                decision=policy_decision.decision,
                executed=False,
                metadata=(
                    self._merged_metadata(base_metadata, dict(policy_decision.metadata))
                    if extended_lifecycle
                    else None
                ),
            )
            if self.lifecycle_hook is not None:
                latest_parent_id = self.lifecycle_hook.before_execution(
                    request,
                    correlation_id=correlation_id,
                    parent_event_id=parent_event.event_id,
                )
            else:
                latest_parent_id = parent_event.event_id
            parent_event = self._emit(
                recorder,
                request,
                EventType.EXECUTION_STARTED,
                correlation_id,
                latest_parent_id,
                rule_id=policy_decision.rule_id,
                decision=policy_decision.decision,
                metadata=(
                    self._merged_metadata(
                        base_metadata,
                        {"execution_attempted": True},
                    )
                    if extended_lifecycle
                    else None
                ),
            )
            tool_completed = False
            try:
                tool_result = self.protected_tool.execute(request)
                tool_completed = True
                terminal_metadata = (
                    {}
                    if self.lifecycle_hook is None
                    else dict(self.lifecycle_hook.after_execution_success(request, tool_result))
                )
            except Exception as error:
                failure_metadata = (
                    {}
                    if self.lifecycle_hook is None
                    else dict(self.lifecycle_hook.after_execution_failure(request, error))
                )
                effect_possible = tool_completed or bool(getattr(error, "effect_possible", False))
                executed_status: bool | None
                if tool_completed:
                    executed_status = True
                elif effect_possible:
                    executed_status = None
                else:
                    executed_status = False
                self._emit(
                    recorder,
                    request,
                    EventType.EXECUTION_FAILED,
                    correlation_id,
                    parent_event.event_id,
                    rule_id=policy_decision.rule_id,
                    decision=policy_decision.decision,
                    executed=executed_status if extended_lifecycle else False,
                    metadata=(
                        self._merged_metadata(
                            base_metadata,
                            {
                                "error_type": type(error).__name__,
                                "execution_attempted": True,
                                "execution_succeeded": tool_completed,
                            },
                            failure_metadata,
                        )
                        if extended_lifecycle
                        else {"error_type": type(error).__name__}
                    ),
                    execution_may_have_started=True,
                )
                raise
            self._emit(
                recorder,
                request,
                EventType.EXECUTION_SUCCEEDED,
                correlation_id,
                parent_event.event_id,
                rule_id=policy_decision.rule_id,
                decision=policy_decision.decision,
                executed=True,
                metadata=(
                    self._merged_metadata(
                        base_metadata,
                        {
                            "execution_attempted": True,
                            "execution_succeeded": True,
                        },
                        terminal_metadata,
                    )
                    if extended_lifecycle
                    else None
                ),
                execution_may_have_started=True,
            )
            return EnforcementResult(
                request=request,
                policy_decision=policy_decision,
                executed=True,
                tool_result=tool_result,
                correlation_id=correlation_id,
            )

        message = "Authorizer returned an unsupported decision; protected action was not executed."
        raise AuthorizationFailure(message)

    @staticmethod
    def _emit(
        recorder: AuditRecorder,
        request: ActionRequest,
        event_type: EventType,
        correlation_id: str,
        parent_event_id: str | None = None,
        rule_id: str | None = None,
        decision: Decision | None = None,
        executed: bool | None = None,
        metadata: Mapping[str, object] | None = None,
        execution_may_have_started: bool = False,
    ) -> SafetyBoxEvent:
        """Translate audit infrastructure errors into the explicit M3 failure."""
        try:
            return recorder.emit(
                request,
                event_type,
                correlation_id=correlation_id,
                parent_event_id=parent_event_id,
                rule_id=rule_id,
                decision=decision,
                executed=executed,
                metadata=metadata,
            )
        except Exception as error:
            raise AuditFailure(
                "Audit recording failed; execution status may be indeterminate.",
                execution_may_have_started=execution_may_have_started,
                failed_event_type=event_type.value,
            ) from error

    @staticmethod
    def _merged_metadata(*values: Mapping[str, object]) -> Mapping[str, object]:
        merged: dict[str, object] = {}
        for value in values:
            merged.update(value)
        return merged

    @staticmethod
    def _safe_error_metadata(error: Exception) -> Mapping[str, object]:
        metadata = getattr(error, "audit_metadata", None)
        if isinstance(metadata, Mapping):
            return dict(metadata)
        return {}
