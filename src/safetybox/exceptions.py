"""Exceptions raised at the SafetyBox enforcement boundary."""

from __future__ import annotations


class AuthorizationFailure(RuntimeError):
    """Raised when authorization cannot complete and M1 fails closed."""


class AuditFailure(RuntimeError):
    """Raised when required M3-compatible audit recording cannot complete."""

    def __init__(
        self,
        message: str,
        *,
        execution_may_have_started: bool = False,
        failed_event_type: str | None = None,
    ) -> None:
        super().__init__(message)
        self.execution_may_have_started = execution_may_have_started
        self.failed_event_type = failed_event_type
