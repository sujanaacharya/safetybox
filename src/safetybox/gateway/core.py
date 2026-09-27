"""Product gateway composing authority, audit, and all effect mediators."""

from __future__ import annotations

import hmac
from pathlib import Path

from safetybox.gateway.audit import AuditLog
from safetybox.gateway.authority import AuthorityEngine
from safetybox.gateway.mediators import (
    FilesystemMediator,
    McpMediator,
    NetworkMediator,
    ProcessMediator,
)
from safetybox.gateway.models import Action, AuthorizationResult
from safetybox.gateway.policy import GatewayPolicy


class Gateway:
    def __init__(
        self,
        policy: GatewayPolicy,
        *,
        audit_directory: Path | None = None,
        approval_token: str | None = None,
    ) -> None:
        self.policy = policy
        self._approval_token = approval_token
        self.audit = AuditLog(audit_directory)
        self.authority = AuthorityEngine(policy)
        self.filesystem = FilesystemMediator(self)
        self.process = ProcessMediator(self)
        self.network = NetworkMediator(self)
        self.mcp = McpMediator(self)

    @classmethod
    def from_policy(
        cls,
        path: str | Path,
        *,
        audit_directory: Path | None = None,
        approval_token: str | None = None,
    ) -> Gateway:
        return cls(
            GatewayPolicy.load(path),
            audit_directory=audit_directory,
            approval_token=approval_token,
        )

    def authorize(self, action: Action) -> AuthorizationResult:
        self.audit.event("requested", action)
        result = self.authority.authorize(action)
        event = {
            "ALLOW": "authorized",
            "FLAG": "authorized",
            "DENY": "denied",
            "REQUIRE_APPROVAL": "approval_requested",
        }[result.decision.value]
        self.audit.event(
            event,
            action,
            decision=result.decision.value,
            action_digest=result.action_digest,
            capability_id=result.capability_id,
            approval_id=result.approval_id,
            forwarded=False,
        )
        return result

    def approve_once(
        self,
        approval_id: str,
        action_digest: str,
        *,
        approver: str,
        approval_token: str,
    ) -> None:
        if self._approval_token is None or not hmac.compare_digest(
            approval_token, self._approval_token
        ):
            raise PermissionError("Valid operator approval credentials are required")
        approval = self.authority.approve_once(approval_id, action_digest, approver=approver)
        pending_action = Action(
            self.policy.principal,
            self.policy.agent,
            self.policy.task,
            "approval.grant",
            approval_id,
            {"approved_action_digest": action_digest, "approver": approver},
        )
        self.audit.event(
            "approval_granted",
            pending_action,
            approval_id=approval_id,
            approved_action_digest=action_digest,
            approver=approver,
            capability_id=approval.capability_id,
        )

    def deny_approval(self, approval_id: str) -> bool:
        denied = self.authority.deny_approval(approval_id)
        action = Action(
            self.policy.principal,
            self.policy.agent,
            self.policy.task,
            "approval.deny",
            approval_id,
        )
        self.audit.event("approval_denied", action, pending_request_found=denied)
        return denied
