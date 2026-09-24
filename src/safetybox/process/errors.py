"""Stable, non-sensitive process mediation errors."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from safetybox.process.primitive import ProcessObservation


class ProcessMediationError(RuntimeError):
    """Base error with stable code and public-safe message."""

    effect_possible = False

    def __init__(
        self,
        code: str,
        safe_message: str,
        *,
        cause: Exception | None = None,
        observation: ProcessObservation | None = None,
    ) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message
        self.observation = observation
        if cause is not None:
            self.__cause__ = cause


class ProcessCanonicalizationError(ProcessMediationError):
    """A request value has no accepted lexical representation."""


class ProcessValidationError(ProcessMediationError):
    """Post-authorization physical validation rejected a target."""


class ProcessSpawnError(ProcessMediationError):
    """The primitive established that no direct child was created."""


class ProcessExecutionError(ProcessMediationError):
    """A confirmed direct child ended unsuccessfully."""

    effect_possible = True


class ProcessTimeoutError(ProcessExecutionError):
    """A direct child exceeded its declared timeout."""


class ProcessSignalError(ProcessExecutionError):
    """A direct child terminated by signal."""


class ProcessNonzeroExitError(ProcessExecutionError):
    """A direct child exited with a nonzero status."""


class ProcessIndeterminateError(ProcessExecutionError):
    """Child creation or post-spawn completion evidence is uncertain."""
