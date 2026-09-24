"""Lexical logical-to-host mapping with no requested-target inspection."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from safetybox.filesystem.canonicalization import canonicalize_logical_path
from safetybox.filesystem.errors import CanonicalizationError


@dataclass(frozen=True, slots=True)
class LogicalHostMapper:
    """Map canonical logical components beneath one explicit trusted host root."""

    host_root: Path

    def __post_init__(self) -> None:
        root = Path(self.host_root)
        if not root.is_absolute():
            raise ValueError("Filesystem host_root must be absolute.")
        if any(part == ".." for part in root.parts):
            raise ValueError("Filesystem host_root must not contain parent traversal.")
        object.__setattr__(self, "host_root", root)

    def to_host(self, canonical_resource: str) -> Path:
        try:
            normalized = canonicalize_logical_path(canonical_resource)
        except CanonicalizationError as error:
            raise ValueError("Resource is not a canonical logical workspace path.") from error
        if normalized != canonical_resource:
            raise ValueError("Resource is not a canonical logical workspace path.")
        relative = canonical_resource.removeprefix("/")
        candidate = self.host_root.joinpath(*relative.split("/"))
        if os.path.commonpath((str(self.host_root), str(candidate))) != str(
            self.host_root
        ):  # pragma: no cover - canonical components make this a defense invariant
            raise ValueError("Mapped host path escapes the configured root.")
        return candidate
