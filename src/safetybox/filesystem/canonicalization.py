"""Pure lexical canonicalization for the logical ``/workspace`` namespace."""

from __future__ import annotations

import unicodedata

from safetybox.filesystem.errors import CanonicalizationError
from safetybox.filesystem.versions import FILESYSTEM_CANONICALIZATION_VERSION

LOGICAL_ROOT = "/workspace"


def canonicalize_logical_path(value: str) -> str:
    """Return one NFC canonical logical path without any filesystem lookup."""
    if not isinstance(value, str):
        raise CanonicalizationError(
            "FS-CANONICALIZATION-TYPE", "Logical paths must be Unicode strings."
        )
    if value == "":
        raise CanonicalizationError(
            "FS-CANONICALIZATION-EMPTY", "The logical path must not be empty."
        )
    if "\x00" in value:
        raise CanonicalizationError(
            "FS-CANONICALIZATION-NUL", "The logical path contains an invalid component."
        )

    normalized = unicodedata.normalize("NFC", value)
    absolute = normalized.startswith("/")
    components = [component for component in normalized.split("/") if component]
    if absolute:
        if not components or components[0] != "workspace":
            raise CanonicalizationError(
                "FS-CANONICALIZATION-OUTSIDE-NAMESPACE",
                "Absolute paths must be in the logical workspace namespace.",
            )
        components = components[1:]

    stack: list[str] = []
    for component in components:
        if component == ".":
            continue
        if component == "..":
            if not stack:
                raise CanonicalizationError(
                    "FS-CANONICALIZATION-ROOT-ESCAPE",
                    "The logical path attempts to escape the workspace root.",
                )
            stack.pop()
            continue
        stack.append(component)

    return LOGICAL_ROOT if not stack else f"{LOGICAL_ROOT}/{'/'.join(stack)}"


__all__ = [
    "FILESYSTEM_CANONICALIZATION_VERSION",
    "LOGICAL_ROOT",
    "canonicalize_logical_path",
]
