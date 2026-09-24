"""Small framework-neutral interfaces used by the reference monitor."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from safetybox.events import SafetyBoxEvent
from safetybox.models import ActionRequest, PolicyDecision


class Authorizer(Protocol):
    """Determines whether an action request may be forwarded."""

    def authorize(self, request: ActionRequest) -> PolicyDecision:
        """Return an authorization decision for ``request``."""


class ProtectedTool(Protocol):
    """Executes an action only after the monitor has authorized it."""

    def execute(self, request: ActionRequest) -> object:
        """Perform the protected operation for ``request``."""


class ExecutionLifecycleHook(Protocol):
    """Optional generic bridge around the monitor's protected execution branch."""

    def before_execution(
        self,
        request: ActionRequest,
        *,
        correlation_id: str,
        parent_event_id: str,
    ) -> str:
        """Run post-allow checks and return the latest committed parent event ID."""

    def after_execution_success(
        self, request: ActionRequest, result: object
    ) -> Mapping[str, object]:
        """Return minimized metadata for a successful terminal event."""

    def after_execution_failure(
        self, request: ActionRequest, error: Exception
    ) -> Mapping[str, object]:
        """Return minimized metadata for a failed terminal event."""


class AuditSink(Protocol):
    """Receives one immutable event at a time."""

    def record(self, event: SafetyBoxEvent) -> None:
        """Persist or otherwise accept a committed event."""
