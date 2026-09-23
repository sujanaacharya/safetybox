"""Exceptions raised at the SafetyBox enforcement boundary."""

from __future__ import annotations


class AuthorizationFailure(RuntimeError):
    """Raised when authorization cannot complete and M1 fails closed."""


class AuditFailure(RuntimeError):
    """Raised when required M3 audit recording cannot complete."""
