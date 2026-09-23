"""The minimal deterministic reference monitor."""

from __future__ import annotations

from dataclasses import dataclass

from safetybox.exceptions import AuthorizationFailure
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

    def execute(self, request: ActionRequest) -> EnforcementResult:
        """Authorize ``request`` and forward it only after an explicit allow."""
        try:
            policy_decision = self.authorizer.authorize(request)
        except Exception as error:
            message = "Authorization failed; protected action was not executed."
            raise AuthorizationFailure(message) from error

        if policy_decision.decision is Decision.DENY:
            return EnforcementResult(
                request=request,
                policy_decision=policy_decision,
                executed=False,
            )

        if policy_decision.decision is Decision.ALLOW:
            tool_result = self.protected_tool.execute(request)
            return EnforcementResult(
                request=request,
                policy_decision=policy_decision,
                executed=True,
                tool_result=tool_result,
            )

        message = "Authorizer returned an unsupported decision; protected action was not executed."
        raise AuthorizationFailure(message)
