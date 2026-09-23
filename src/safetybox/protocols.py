"""Small framework-neutral interfaces used by the reference monitor."""

from __future__ import annotations

from typing import Protocol

from safetybox.models import ActionRequest, PolicyDecision


class Authorizer(Protocol):
    """Determines whether an action request may be forwarded."""

    def authorize(self, request: ActionRequest) -> PolicyDecision:
        """Return an authorization decision for ``request``."""


class ProtectedTool(Protocol):
    """Executes an action only after the monitor has authorized it."""

    def execute(self, request: ActionRequest) -> object:
        """Perform the protected operation for ``request``."""
