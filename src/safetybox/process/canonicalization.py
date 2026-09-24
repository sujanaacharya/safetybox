"""Pure lexical PMED-L1 canonicalization and argv commitments."""

from __future__ import annotations

import hashlib
import json

from safetybox.filesystem.canonicalization import canonicalize_logical_path
from safetybox.filesystem.errors import CanonicalizationError
from safetybox.process.errors import ProcessCanonicalizationError
from safetybox.process.models import ArgumentCommitment

ARGV_MAX_COUNT = 64
ARGV_ELEMENT_MAX_UTF8_BYTES = 4096
ARGV_TOTAL_MAX_UTF8_BYTES = 16384
TIMEOUT_MIN_MS = 50
TIMEOUT_MAX_MS = 2000


def canonicalize_executable(value: str) -> str:
    """Return one absolute POSIX spelling without consulting host state."""
    if not isinstance(value, str):
        raise ProcessCanonicalizationError(
            "PROC-CANONICALIZATION-EXECUTABLE-TYPE",
            "Executable must be a Unicode string.",
        )
    if not value:
        raise ProcessCanonicalizationError(
            "PROC-CANONICALIZATION-EXECUTABLE-EMPTY",
            "Executable must not be empty.",
        )
    if "\x00" in value:
        raise ProcessCanonicalizationError(
            "PROC-CANONICALIZATION-EXECUTABLE-NUL",
            "Executable contains an invalid component.",
        )
    if not value.startswith("/"):
        raise ProcessCanonicalizationError(
            "PROC-CANONICALIZATION-EXECUTABLE-RELATIVE",
            "Executable must be an absolute POSIX path.",
        )
    stack: list[str] = []
    for component in value.split("/"):
        if component in {"", "."}:
            continue
        if component == "..":
            if stack:
                stack.pop()
            continue
        stack.append(component)
    return "/" if not stack else f"/{'/'.join(stack)}"


def canonicalize_process_cwd(value: str) -> str:
    """Apply frozen /workspace rules while rejecting all relative cwd input."""
    if not isinstance(value, str):
        raise ProcessCanonicalizationError(
            "PROC-CANONICALIZATION-CWD-TYPE", "Cwd must be a Unicode string."
        )
    if not value.startswith("/"):
        raise ProcessCanonicalizationError(
            "PROC-CANONICALIZATION-CWD-RELATIVE",
            "Cwd must be an absolute logical workspace path.",
        )
    try:
        return canonicalize_logical_path(value)
    except CanonicalizationError as error:
        raise ProcessCanonicalizationError(
            "PROC-CANONICALIZATION-CWD",
            "Cwd is not a valid logical workspace path.",
            cause=error,
        ) from error


def commit_argv(
    argv: tuple[str, ...],
) -> tuple[tuple[ArgumentCommitment, ...], str]:
    """Validate immutable argv and return ordered non-reversible commitments."""
    if len(argv) > ARGV_MAX_COUNT:
        raise ProcessCanonicalizationError(
            "PROC-CANONICALIZATION-ARGV-COUNT", "Argv contains too many elements."
        )
    encoded_values: list[bytes] = []
    commitments: list[ArgumentCommitment] = []
    for index, value in enumerate(argv):
        if not isinstance(value, str):
            raise ProcessCanonicalizationError(
                "PROC-CANONICALIZATION-ARGV-TYPE",
                "Every argv element must be a Unicode string.",
            )
        if "\x00" in value:
            raise ProcessCanonicalizationError(
                "PROC-CANONICALIZATION-ARGV-NUL",
                "Argv contains an invalid element.",
            )
        encoded = value.encode("utf-8")
        if len(encoded) > ARGV_ELEMENT_MAX_UTF8_BYTES:
            raise ProcessCanonicalizationError(
                "PROC-CANONICALIZATION-ARGV-ELEMENT-SIZE",
                "An argv element exceeds the byte limit.",
            )
        encoded_values.append(encoded)
        commitments.append(
            ArgumentCommitment(index, len(encoded), hashlib.sha256(encoded).hexdigest())
        )
    if sum(map(len, encoded_values)) > ARGV_TOTAL_MAX_UTF8_BYTES:
        raise ProcessCanonicalizationError(
            "PROC-CANONICALIZATION-ARGV-TOTAL-SIZE",
            "Argv exceeds the total byte limit.",
        )
    serialized = json.dumps(
        [value.decode("utf-8") for value in encoded_values],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return tuple(commitments), hashlib.sha256(serialized).hexdigest()


def validate_timeout(timeout_ms: int) -> None:
    if isinstance(timeout_ms, bool) or not isinstance(timeout_ms, int):
        raise ProcessCanonicalizationError(
            "PROC-CANONICALIZATION-TIMEOUT-TYPE", "Timeout must be an integer."
        )
    if not TIMEOUT_MIN_MS <= timeout_ms <= TIMEOUT_MAX_MS:
        raise ProcessCanonicalizationError(
            "PROC-CANONICALIZATION-TIMEOUT-RANGE",
            "Timeout must be between 50 and 2000 milliseconds.",
        )
