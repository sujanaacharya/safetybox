"""Post-authorization executable and cwd validation for PMED-L1."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from safetybox.filesystem.mapping import LogicalHostMapper
from safetybox.process.errors import ProcessValidationError


@dataclass(frozen=True, slots=True)
class ValidatedProcessTargets:
    executable: str
    cwd: Path


@dataclass(frozen=True, slots=True)
class ProcessTargetValidator:
    mapper: LogicalHostMapper

    def validate(self, executable: str, logical_cwd: str) -> ValidatedProcessTargets:
        self.validate_executable(executable)
        cwd = self.validate_cwd(logical_cwd)
        return ValidatedProcessTargets(executable, cwd)

    @staticmethod
    def _components(path: Path) -> tuple[Path, ...]:
        current = Path(path.anchor)
        values: list[Path] = []
        for component in path.parts[1:]:
            current = current / component
            values.append(current)
        return tuple(values)

    def validate_executable(self, executable: str) -> None:
        path = Path(executable)
        components = self._components(path)
        for index, component in enumerate(components):
            try:
                status = os.lstat(component)
            except FileNotFoundError as error:
                raise ProcessValidationError(
                    "PROC-VALIDATION-EXECUTABLE-NOT-FOUND",
                    "The authorized executable does not exist.",
                    cause=error,
                ) from error
            except OSError as error:
                raise ProcessValidationError(
                    "PROC-VALIDATION-EXECUTABLE-INSPECTION",
                    "Executable validation could not complete safely.",
                    cause=error,
                ) from error
            if stat.S_ISLNK(status.st_mode):
                raise ProcessValidationError(
                    "PROC-VALIDATION-EXECUTABLE-SYMLINK",
                    "Executable validation rejected a symlink component.",
                )
            terminal = index == len(components) - 1
            if terminal:
                if not stat.S_ISREG(status.st_mode):
                    raise ProcessValidationError(
                        "PROC-VALIDATION-EXECUTABLE-TYPE",
                        "The authorized executable is not a regular file.",
                    )
            elif not stat.S_ISDIR(status.st_mode):
                raise ProcessValidationError(
                    "PROC-VALIDATION-EXECUTABLE-ANCESTOR",
                    "An executable path ancestor is not a directory.",
                )
        if not components:  # '/' is a directory and therefore not executable here.
            raise ProcessValidationError(
                "PROC-VALIDATION-EXECUTABLE-TYPE",
                "The authorized executable is not a regular file.",
            )
        if not os.access(path, os.X_OK, follow_symlinks=False):
            raise ProcessValidationError(
                "PROC-VALIDATION-EXECUTABLE-PERMISSION",
                "The authorized executable is not executable by this process.",
            )
        descriptor: int | None = None
        try:
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(path, flags)
            header = os.read(descriptor, 4)
        except OSError as error:
            raise ProcessValidationError(
                "PROC-VALIDATION-EXECUTABLE-READ",
                "Executable format validation could not complete safely.",
                cause=error,
            ) from error
        finally:
            if descriptor is not None:
                os.close(descriptor)
        if header.startswith(b"#!") or header != b"\x7fELF":
            raise ProcessValidationError(
                "PROC-VALIDATION-EXECUTABLE-FORMAT",
                "PMED-L1 accepts only native ELF executables, not scripts or wrappers.",
            )

    def validate_cwd(self, logical_cwd: str) -> Path:
        cwd = self.mapper.to_host(logical_cwd)
        try:
            relative = cwd.relative_to(self.mapper.host_root)
        except ValueError as error:  # pragma: no cover - mapper invariant
            raise ProcessValidationError(
                "PROC-VALIDATION-CWD-ESCAPE", "Mapped cwd is outside the injected root."
            ) from error
        current = self.mapper.host_root
        for index, component in enumerate(relative.parts):
            current = current / component
            try:
                status = os.lstat(current)
            except FileNotFoundError as error:
                raise ProcessValidationError(
                    "PROC-VALIDATION-CWD-NOT-FOUND",
                    "The authorized cwd does not exist.",
                    cause=error,
                ) from error
            except OSError as error:
                raise ProcessValidationError(
                    "PROC-VALIDATION-CWD-INSPECTION",
                    "Cwd validation could not complete safely.",
                    cause=error,
                ) from error
            if stat.S_ISLNK(status.st_mode):
                raise ProcessValidationError(
                    "PROC-VALIDATION-CWD-SYMLINK",
                    "Cwd validation rejected a symlink component.",
                )
            terminal = index == len(relative.parts) - 1
            if not stat.S_ISDIR(status.st_mode):
                code = "PROC-VALIDATION-CWD-TYPE" if terminal else "PROC-VALIDATION-CWD-ANCESTOR"
                raise ProcessValidationError(code, "The authorized cwd is not a directory.")
        return cwd
