"""Deterministic M1 policy implementations."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from safetybox.models import ActionRequest, Decision, PolicyDecision

ActionResource = tuple[str, str]


@dataclass(frozen=True, slots=True)
class StaticPolicy:
    """Allow explicitly listed action/resource pairs and deny all other requests."""

    allowed: frozenset[ActionResource] = field(default_factory=frozenset)

    def __init__(self, allowed: Iterable[ActionResource] = ()) -> None:
        object.__setattr__(self, "allowed", frozenset(allowed))

    def authorize(self, request: ActionRequest) -> PolicyDecision:
        pair = (request.action, request.resource)
        if pair in self.allowed:
            return PolicyDecision(
                decision=Decision.ALLOW,
                rule_id="POL-M1-ALLOWLIST",
                reason="Action and resource are explicitly allowed by the M1 static policy.",
            )
        return PolicyDecision(
            decision=Decision.DENY,
            rule_id="POL-M1-DEFAULT-DENY",
            reason="No M1 static-policy allow rule matches this action and resource.",
        )
