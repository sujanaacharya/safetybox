"""The minimal deterministic reference monitor."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from safetybox.audit import AuditRecorder, InMemoryAuditSink
from safetybox.events import EventType, SafetyBoxEvent
from safetybox.exceptions import AuditFailure, AuthorizationFailure
from safetybox.models import ActionRequest, Decision, EnforcementResult
from safetybox.protocols import Authorizer, ProtectedTool


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

    def execute(self, request: ActionRequest) -> EnforcementResult:
        """Authorize ``request`` and forward it only after an explicit allow."""
        recorder = self.audit_recorder
        correlation_id = request.request_id
        parent_event = self._emit(recorder, request, EventType.ACTION_REQUESTED, correlation_id)
        parent_event = self._emit(
            recorder,
            request,
            EventType.AUTHORIZATION_STARTED,
            correlation_id,
            parent_event.event_id,
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
                metadata={"error_type": type(error).__name__},
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
            )
            parent_event = self._emit(
                recorder,
                request,
                EventType.EXECUTION_STARTED,
                correlation_id,
                parent_event.event_id,
                rule_id=policy_decision.rule_id,
                decision=policy_decision.decision,
            )
            try:
                tool_result = self.protected_tool.execute(request)
            except Exception as error:
                self._emit(
                    recorder,
                    request,
                    EventType.EXECUTION_FAILED,
                    correlation_id,
                    parent_event.event_id,
                    rule_id=policy_decision.rule_id,
                    decision=policy_decision.decision,
                    executed=False,
                    metadata={"error_type": type(error).__name__},
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
                "Audit recording failed; execution status may be indeterminate."
            ) from error
