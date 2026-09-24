"""Typed public error categories for filesystem mediation."""

from __future__ import annotations


class FilesystemMediationError(RuntimeError):
    """Base class carrying a stable code and a non-sensitive public message."""

    effect_possible = False

    def __init__(self, code: str, safe_message: str, *, cause: Exception | None = None) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message
        if cause is not None:
            self.__cause__ = cause


class CanonicalizationError(FilesystemMediationError):
    """The untrusted logical path has no accepted canonical representation."""


class TargetValidationError(FilesystemMediationError):
    """Post-allow physical validation rejected the target safely."""


class FilesystemToolError(FilesystemMediationError):
    """The authorized operation failed with no observed or expected partial effect."""


class FilesystemIndeterminateError(FilesystemMediationError):
    """The authorized operation may have produced an effect before failing."""

    effect_possible = True


class FilesystemPrimitiveError(FilesystemMediationError):
    """A real primitive failed with an explicit effect-possibility classification."""

    def __init__(
        self,
        code: str,
        safe_message: str,
        *,
        effect_possible: bool,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(code, safe_message, cause=cause)
        self.effect_possible = effect_possible
