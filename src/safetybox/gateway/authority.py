"""Deterministic task-bound authorization and exact one-shot approval."""

from __future__ import annotations

import fnmatch
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from safetybox.gateway.canonical import action_digest, canonical_value
from safetybox.gateway.models import (
    Action,
    ApprovalCapability,
    Authority,
    AuthorizationResult,
    Decision,
    PendingApproval,
)
from safetybox.gateway.policy import GatewayPolicy

APPROVAL_PLACEHOLDER = "approval-required"


class AuthorityEngine:
    def __init__(self, policy: GatewayPolicy) -> None:
        self.policy = policy
        self.pending: dict[str, PendingApproval] = {}
        self.approvals: dict[str, ApprovalCapability] = {}

    def authorize(self, action: Action) -> AuthorizationResult:
        identity_error = self._identity_error(action)
        if identity_error:
            return self._result(Decision.DENY, False, action, "identity-rejected", identity_error)
        if self._rule_matches(self.policy.denied, action):
            return self._result(
                Decision.DENY, False, action, "explicit-deny", "Explicit deny rule matched"
            )

        capability = next(
            (cap for cap in self.policy.capabilities if self._cap_matches(cap, action)), None
        )
        if capability is not None:
            flagged = self._rule_matches(self.policy.flags, action)
            decision = Decision.FLAG if flagged else Decision.ALLOW
            reason = "Authorized; policy flag recorded" if flagged else "Capability matched"
            return self._result(decision, True, action, capability.capability_id, reason)

        approval = self._matching_approval(action)
        if approval is not None:
            return self._result(
                Decision.ALLOW,
                True,
                action,
                approval.capability_id,
                "Exact one-shot approval capability matched",
                approval.approval_id,
            )

        if self._rule_matches(self.policy.approval_required, action):
            result = self._result(
                Decision.REQUIRE_APPROVAL,
                False,
                action,
                APPROVAL_PLACEHOLDER,
                "Explicit authority expansion required",
            )
            approval_id = str(uuid4())
            self.pending[approval_id] = PendingApproval(
                approval_id, result.action_digest, action, datetime.now(UTC)
            )
            return replace(result, approval_id=approval_id)
        return self._result(Decision.DENY, False, action, "no-capability", "No capability matched")

    def approve_once(
        self, approval_id: str, action_digest_value: str, *, approver: str
    ) -> ApprovalCapability:
        pending = self.pending.get(approval_id)
        if pending is None or pending.action_digest != action_digest_value:
            raise ValueError("Approval request is missing or action digest does not match")
        del self.pending[approval_id]
        issued = datetime.now(UTC)
        capability = ApprovalCapability(
            approval_id=approval_id,
            capability_id=f"approval:{approval_id}",
            action_digest=action_digest_value,
            approver=approver,
            issued_at=issued,
            expires_at=issued + timedelta(minutes=10),
        )
        self.approvals[approval_id] = capability
        return capability

    def deny_approval(self, approval_id: str) -> bool:
        return self.pending.pop(approval_id, None) is not None

    def consume(self, result: AuthorizationResult) -> None:
        if result.approval_id is None:
            return
        approval = self.approvals.get(result.approval_id)
        if approval is None or approval.used:
            raise RuntimeError("Approval capability is unavailable or already used")
        self.approvals[result.approval_id] = replace(approval, used=True)

    def _matching_approval(self, action: Action) -> ApprovalCapability | None:
        now = datetime.now(UTC)
        for approval in self.approvals.values():
            if approval.used or approval.expires_at <= now:
                continue
            candidate = self._digest(action, approval.capability_id)
            # The request digest initially used an approval placeholder. Rebind the exact
            # pending action to the new explicit capability without weakening action equality.
            pending_digest = self._digest(action, APPROVAL_PLACEHOLDER)
            if pending_digest == approval.action_digest and candidate:
                return approval
        return None

    def _result(
        self,
        decision: Decision,
        authorized: bool,
        action: Action,
        capability_id: str,
        reason: str,
        approval_id: str | None = None,
    ) -> AuthorizationResult:
        return AuthorizationResult(
            decision,
            authorized,
            self._digest(action, capability_id),
            self.policy.policy_digest,
            None
            if capability_id in {"identity-rejected", "explicit-deny", "no-capability"}
            else capability_id,
            reason,
            approval_id,
        )

    def _digest(self, action: Action, capability_id: str) -> str:
        return action_digest(
            subject=action.subject,
            agent=action.agent,
            task=action.task,
            operation=action.operation,
            resource=action.resource,
            arguments=action.arguments,
            capability_id=capability_id,
            policy_digest=self.policy.policy_digest,
        )

    def _identity_error(self, action: Action) -> str | None:
        if action.subject != self.policy.principal:
            return "Principal substitution rejected"
        if action.agent != self.policy.agent:
            return "Agent identity substitution rejected"
        if action.task != self.policy.task:
            return "Task substitution rejected"
        return None

    def _cap_matches(self, cap: Authority, action: Action) -> bool:
        if (cap.principal, cap.agent, cap.task, cap.action) != (
            action.subject,
            action.agent,
            action.task,
            action.operation,
        ):
            return False
        if cap.expires_at is not None and cap.expires_at <= datetime.now(UTC):
            return False
        return _resource_matches(cap.resource, action.resource) and _constraints_match(
            cap.constraints, action.arguments
        )

    @staticmethod
    def _rule_matches(rules: tuple[Mapping[str, Any], ...], action: Action) -> bool:
        return any(
            ("action" not in rule or rule["action"] == action.operation)
            and (
                "resource" not in rule or _resource_matches(str(rule["resource"]), action.resource)
            )
            for rule in rules
        )


def _resource_matches(scope: str, resource: str) -> bool:
    if scope.endswith("/**"):
        root = scope[:-3].rstrip("/")
        return resource == root or resource.startswith(root + "/")
    if "*" in scope:
        return fnmatch.fnmatchcase(resource, scope)
    return scope == resource


def _constraints_match(constraints: Mapping[str, Any], arguments: Mapping[str, Any]) -> bool:
    for key, expected in constraints.items():
        actual = arguments.get(key)
        if key.startswith("allowed_"):
            argument_key = key.removeprefix("allowed_")
            actual = arguments.get(argument_key)
            if not any(canonical_value(actual) == canonical_value(item) for item in expected):
                return False
        elif canonical_value(actual) != canonical_value(expected):
            return False
    return True
