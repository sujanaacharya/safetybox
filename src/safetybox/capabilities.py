"""Minimal deterministic capability evaluation for M2."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

from safetybox.models import ActionRequest, Decision, PolicyDecision

if TYPE_CHECKING:
    from safetybox.contracts import TaskContract


def _is_canonical_absolute_path(value: str) -> bool:
    """Return whether ``value`` is M2's accepted absolute path representation."""
    if not value.startswith("/") or value == "/":
        return False
    segments = value[1:].split("/")
    return all(segment not in {"", ".", ".."} for segment in segments)


def is_valid_resource_scope(scope: str) -> bool:
    """Return whether ``scope`` is a valid M2 exact or path-subtree scope."""
    if not scope:
        return False
    if scope.endswith("/**"):
        return _is_canonical_absolute_path(scope.removesuffix("/**"))
    if scope.startswith("/"):
        return _is_canonical_absolute_path(scope)
    return True


def resource_matches(scope: str, resource: str) -> bool:
    """Match an exact logical resource or a canonical absolute-path subtree.

    M2 supports exact string matches for all resource identifiers. A scope ending
    in ``/**`` additionally permits canonical absolute-path descendants of its
    root. The root itself is not a descendant. No filesystem resolution occurs.
    """
    if scope.endswith("/**"):
        root = scope.removesuffix("/**")
        return (
            _is_canonical_absolute_path(root)
            and _is_canonical_absolute_path(resource)
            and resource.startswith(f"{root}/")
        )
    return scope == resource


@dataclass(frozen=True, slots=True)
class Capability:
    """Explicit authority for one action and an exact resource or path subtree."""

    action: str
    resource: str

    def __post_init__(self) -> None:
        if not self.action:
            raise ValueError("Capability action must not be empty.")
        if not self.resource:
            raise ValueError("Capability resource must not be empty.")
        if not is_valid_resource_scope(self.resource):
            raise ValueError("Capability must use a valid exact or path-subtree resource scope.")

    def matches(self, request: ActionRequest) -> bool:
        """Return whether this capability authorizes the request action/resource."""
        return self.action == request.action and resource_matches(self.resource, request.resource)


@dataclass(frozen=True, slots=True)
class CapabilityEvaluator:
    """Evaluate a request against one immutable task contract."""

    def evaluate(self, contract: TaskContract, request: ActionRequest) -> PolicyDecision:
        """Return an allow only for an explicit task-bound capability match."""
        if request.task_id != contract.task_id:
            return PolicyDecision(
                Decision.DENY,
                "POL-M2-TASK-MISMATCH",
                "Request task does not match the task contract.",
                {
                    "authority_source": "TaskContract",
                    "contract_task_id": contract.task_id,
                    "applicable_capability": None,
                },
            )

        action_capabilities = tuple(
            capability
            for capability in contract.capabilities
            if capability.action == request.action
        )
        if not action_capabilities:
            return PolicyDecision(
                Decision.DENY,
                "POL-M2-CAPABILITY-MISSING",
                "No capability grants the requested action.",
                {
                    "authority_source": "TaskContract",
                    "contract_task_id": contract.task_id,
                    "applicable_capability": None,
                },
            )

        matching = min(
            (capability for capability in action_capabilities if capability.matches(request)),
            key=lambda capability: capability.resource,
            default=None,
        )
        if matching is not None:
            return PolicyDecision(
                Decision.ALLOW,
                "POL-M2-CAPABILITY-ALLOW",
                "An explicit task capability matches the requested action and resource.",
                {
                    "authority_source": "TaskContract",
                    "contract_task_id": contract.task_id,
                    "applicable_capability": MappingProxyType(
                        {"action": matching.action, "resource": matching.resource}
                    ),
                },
            )

        return PolicyDecision(
            Decision.DENY,
            "POL-M2-RESOURCE-OUT-OF-SCOPE",
            "The requested resource is outside every scope for the requested action.",
            {
                "authority_source": "TaskContract",
                "contract_task_id": contract.task_id,
                "applicable_capability": None,
            },
        )
