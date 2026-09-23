"""Exceptions raised at the SafetyBox enforcement boundary."""

from __future__ import annotations


class AuthorizationFailure(RuntimeError):
    """Raised when authorization cannot complete and M1 fails closed."""
