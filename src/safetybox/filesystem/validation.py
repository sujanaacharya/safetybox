"""Post-authorization no-follow physical validation."""

from __future__ import annotations

import stat
from dataclasses import dataclass
from pathlib import Path

from safetybox.filesystem.canonicalization import LOGICAL_ROOT
from safetybox.filesystem.errors import FilesystemToolError, TargetValidationError
from safetybox.filesystem.mapping import LogicalHostMapper
from safetybox.filesystem.models import FilesystemEntryType, FilesystemOperation
from safetybox.filesystem.primitives import RealFilesystemPrimitives


@dataclass(frozen=True, slots=True)
class ValidatedTargets:
    source: Path
    source_type: FilesystemEntryType | None
    destination: Path | None = None
    destination_type: FilesystemEntryType | None = None


@dataclass(frozen=True, slots=True)
class _Inspection:
    path: Path
    exists: bool
    entry_type: FilesystemEntryType | None
    link_count: int | None
    missing_index: int | None
    component_count: int


@dataclass(frozen=True, slots=True)
class PhysicalTargetValidator:
    mapper: LogicalHostMapper
    primitives: RealFilesystemPrimitives

    def validate(
        self,
        operation: FilesystemOperation,
        resource: str,
        destination: str | None = None,
    ) -> ValidatedTargets:
        if resource == LOGICAL_ROOT and operation not in {
            FilesystemOperation.LIST,
            FilesystemOperation.STAT,
        }:
            raise TargetValidationError(
                "EXP014-TARGET-ROOT-REJECT",
                "This operation cannot target the logical workspace root.",
            )
        source = self._inspect(resource)
        if operation in {
            FilesystemOperation.READ,
            FilesystemOperation.WRITE,
            FilesystemOperation.APPEND,
        }:
            self._require_existing(source)
            self._require_type(source, FilesystemEntryType.FILE)
            self._reject_hard_link(source)
        elif operation in {FilesystemOperation.CREATE, FilesystemOperation.MKDIR}:
            self._require_absent_leaf_with_parent(source)
        elif operation is FilesystemOperation.DELETE:
            self._require_existing(source)
            if source.entry_type is FilesystemEntryType.FILE:
                self._reject_hard_link(source)
            elif source.entry_type is not FilesystemEntryType.DIRECTORY:
                self._unsupported_type()
        elif operation is FilesystemOperation.LIST:
            self._require_existing(source)
            self._require_type(source, FilesystemEntryType.DIRECTORY)
        elif operation is FilesystemOperation.STAT:
            self._require_existing(source)
            if source.entry_type is FilesystemEntryType.FILE:
                self._reject_hard_link(source)
            elif source.entry_type is not FilesystemEntryType.DIRECTORY:
                self._unsupported_type()
        elif operation is FilesystemOperation.RENAME:
            if destination is None:  # pragma: no cover - request model invariant
                raise ValueError("rename destination is required")
            return self._validate_rename(source, destination)
        else:  # pragma: no cover - closed enum
            raise ValueError("unsupported filesystem operation")
        return ValidatedTargets(source.path, source.entry_type)

    def _validate_rename(self, source: _Inspection, destination: str) -> ValidatedTargets:
        if destination == LOGICAL_ROOT:
            raise TargetValidationError(
                "EXP014-TARGET-ROOT-REJECT",
                "Rename cannot target the logical workspace root.",
            )
        self._require_existing(source)
        if source.entry_type is FilesystemEntryType.FILE:
            self._reject_hard_link(source)
        elif source.entry_type is FilesystemEntryType.DIRECTORY:
            if not self.primitives.directory_is_empty(source.path):
                raise FilesystemToolError(
                    "FS-TOOL-RENAME-NONEMPTY-SOURCE",
                    "Rename supports only an empty source directory.",
                )
        else:
            self._unsupported_type()

        target = self._inspect(destination)
        if not target.exists:
            self._require_absent_leaf_with_parent(target)
        else:
            if target.entry_type is not source.entry_type:
                raise FilesystemToolError(
                    "FS-TOOL-RENAME-INCOMPATIBLE-TARGET",
                    "The existing rename destination has an incompatible type.",
                )
            if target.entry_type is FilesystemEntryType.FILE:
                self._reject_hard_link(target)
            elif not self.primitives.directory_is_empty(target.path):
                raise FilesystemToolError(
                    "FS-TOOL-RENAME-NONEMPTY-DESTINATION",
                    "Rename cannot replace a non-empty destination directory.",
                )
        return ValidatedTargets(source.path, source.entry_type, target.path, target.entry_type)

    def _inspect(self, logical_path: str) -> _Inspection:
        terminal = self.mapper.to_host(logical_path)
        relative_parts = terminal.relative_to(self.mapper.host_root).parts
        current = self.mapper.host_root
        for index, component in enumerate(relative_parts):
            current = current / component
            try:
                status = self.primitives.lstat(current)
            except FileNotFoundError:
                return _Inspection(terminal, False, None, None, index, len(relative_parts))
            except OSError as error:
                raise TargetValidationError(
                    "EXP014-TARGET-INSPECTION-FAILED",
                    "Physical target validation could not complete safely.",
                    cause=error,
                ) from error
            if stat.S_ISLNK(status.st_mode):
                raise TargetValidationError(
                    "EXP014-TARGET-SYMLINK-REJECT",
                    "Physical target validation rejected a symlink component.",
                )
            terminal_component = index == len(relative_parts) - 1
            if not terminal_component and not stat.S_ISDIR(status.st_mode):
                raise FilesystemToolError(
                    "FS-TOOL-PARENT-NOT-DIRECTORY",
                    "An existing path ancestor is not a directory.",
                )
            if terminal_component:
                if stat.S_ISREG(status.st_mode):
                    entry_type = FilesystemEntryType.FILE
                elif stat.S_ISDIR(status.st_mode):
                    entry_type = FilesystemEntryType.DIRECTORY
                else:
                    entry_type = None
                return _Inspection(
                    terminal,
                    True,
                    entry_type,
                    status.st_nlink,
                    None,
                    len(relative_parts),
                )
        raise AssertionError("canonical workspace paths always contain a component")

    @staticmethod
    def _require_existing(target: _Inspection) -> None:
        if not target.exists:
            raise FilesystemToolError("FS-TOOL-NOT-FOUND", "The authorized target does not exist.")

    @staticmethod
    def _require_absent_leaf_with_parent(target: _Inspection) -> None:
        if target.exists:
            raise FilesystemToolError(
                "FS-TOOL-TARGET-EXISTS", "The authorized target already exists."
            )
        if target.missing_index != target.component_count - 1:
            raise FilesystemToolError(
                "FS-TOOL-PARENT-NOT-FOUND",
                "The authorized target's immediate parent does not exist.",
            )

    @staticmethod
    def _require_type(target: _Inspection, expected: FilesystemEntryType) -> None:
        if target.entry_type is not expected:
            raise FilesystemToolError(
                "FS-TOOL-TYPE-MISMATCH", "The authorized target has the wrong type."
            )

    @staticmethod
    def _reject_hard_link(target: _Inspection) -> None:
        if target.link_count is not None and target.link_count > 1:
            raise TargetValidationError(
                "EXP014-TARGET-HARDLINK-REJECT",
                "Physical target validation rejected a multi-link regular file.",
            )

    @staticmethod
    def _unsupported_type() -> None:
        raise FilesystemToolError(
            "FS-TOOL-UNSUPPORTED-TYPE", "The authorized target type is unsupported."
        )
