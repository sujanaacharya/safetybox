"""Minimal deterministic capability evaluation for M2."""

from __future__ import annotations

from dataclasses import dataclass
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
        is_path = self.resource.startswith("/")
        is_subtree = self.resource.endswith("/**")
        if is_path and not is_subtree and not _is_canonical_absolute_path(self.resource):
            raise ValueError("Path capability must use a canonical absolute resource.")
        if self.resource.endswith("/**") and not _is_canonical_absolute_path(
            self.resource.removesuffix("/**")
        ):
            raise ValueError("Path subtree capability must use a canonical absolute root.")

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
            )

        if any(capability.matches(request) for capability in action_capabilities):
            return PolicyDecision(
                Decision.ALLOW,
                "POL-M2-CAPABILITY-ALLOW",
                "An explicit task capability matches the requested action and resource.",
            )

        return PolicyDecision(
            Decision.DENY,
            "POL-M2-RESOURCE-OUT-OF-SCOPE",
            "The requested resource is outside every scope for the requested action.",
        )
