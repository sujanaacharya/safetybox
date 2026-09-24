"""Narrow real-filesystem primitive boundary used after authorization."""

from __future__ import annotations

import os
from pathlib import Path
from stat import S_ISDIR, S_ISREG

from safetybox.filesystem.errors import FilesystemPrimitiveError
from safetybox.filesystem.models import FilesystemEntryType, FilesystemStat


class RealFilesystemPrimitives:
    """All OS calls used by validation and requested filesystem operations.

    Callers must enforce authorization and physical validation before invoking
    requested operations. This class intentionally provides no shell route.
    """

    def lstat(self, path: Path) -> os.stat_result:
        return os.lstat(path)

    def directory_is_empty(self, path: Path) -> bool:
        with os.scandir(path) as entries:
            return next(entries, None) is None

    def read(self, path: Path) -> bytes:
        descriptor: int | None = None
        try:
            descriptor = os.open(path, os.O_RDONLY)
            chunks: list[bytes] = []
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    return b"".join(chunks)
                chunks.append(chunk)
        except OSError as error:
            raise FilesystemPrimitiveError(
                "FS-TOOL-READ",
                "The authorized read primitive failed.",
                effect_possible=False,
                cause=error,
            ) from error
        finally:
            if descriptor is not None:
                os.close(descriptor)

    def write(self, path: Path, data: bytes) -> None:
        descriptor: int | None = None
        effect_possible = False
        try:
            descriptor = os.open(path, os.O_WRONLY)
            os.ftruncate(descriptor, 0)
            effect_possible = True
            self._write_all(descriptor, data)
        except OSError as error:
            raise FilesystemPrimitiveError(
                "FS-TOOL-WRITE",
                "The authorized write primitive failed.",
                effect_possible=effect_possible,
                cause=error,
            ) from error
        finally:
            if descriptor is not None:
                os.close(descriptor)

    def append(self, path: Path, data: bytes) -> None:
        descriptor: int | None = None
        written = 0
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_APPEND)
            while written < len(data):
                count = os.write(descriptor, data[written:])
                if count <= 0:
                    raise OSError("write returned no progress")
                written += count
        except OSError as error:
            raise FilesystemPrimitiveError(
                "FS-TOOL-APPEND",
                "The authorized append primitive failed.",
                effect_possible=written > 0,
                cause=error,
            ) from error
        finally:
            if descriptor is not None:
                os.close(descriptor)

    def create(self, path: Path, data: bytes) -> None:
        descriptor: int | None = None
        created = False
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            created = True
            self._write_all(descriptor, data)
        except OSError as error:
            raise FilesystemPrimitiveError(
                "FS-TOOL-CREATE",
                "The authorized create primitive failed.",
                effect_possible=created,
                cause=error,
            ) from error
        finally:
            if descriptor is not None:
                os.close(descriptor)

    def delete_file(self, path: Path) -> None:
        try:
            os.unlink(path)
        except OSError as error:
            raise FilesystemPrimitiveError(
                "FS-TOOL-DELETE",
                "The authorized delete primitive failed.",
                effect_possible=False,
                cause=error,
            ) from error

    def delete_directory(self, path: Path) -> None:
        try:
            os.rmdir(path)
        except OSError as error:
            raise FilesystemPrimitiveError(
                "FS-TOOL-DELETE",
                "The authorized directory delete primitive failed.",
                effect_possible=False,
                cause=error,
            ) from error

    def rename(self, source: Path, destination: Path) -> None:
        try:
            os.replace(source, destination)
        except OSError as error:
            raise FilesystemPrimitiveError(
                "FS-TOOL-RENAME",
                "The authorized rename primitive failed.",
                effect_possible=False,
                cause=error,
            ) from error

    def mkdir(self, path: Path) -> None:
        try:
            os.mkdir(path, 0o700)
        except OSError as error:
            raise FilesystemPrimitiveError(
                "FS-TOOL-MKDIR",
                "The authorized mkdir primitive failed.",
                effect_possible=False,
                cause=error,
            ) from error

    def list_directory(self, path: Path) -> tuple[str, ...]:
        import unicodedata

        try:
            with os.scandir(path) as entries:
                names = [unicodedata.normalize("NFC", entry.name) for entry in entries]
        except OSError as error:
            raise FilesystemPrimitiveError(
                "FS-TOOL-LIST",
                "The authorized list primitive failed.",
                effect_possible=False,
                cause=error,
            ) from error
        return tuple(sorted(names))

    def minimized_stat(self, path: Path) -> FilesystemStat:
        try:
            status = os.lstat(path)
        except OSError as error:
            raise FilesystemPrimitiveError(
                "FS-TOOL-STAT",
                "The authorized stat primitive failed.",
                effect_possible=False,
                cause=error,
            ) from error
        if S_ISREG(status.st_mode):
            return FilesystemStat(FilesystemEntryType.FILE, status.st_size, status.st_nlink)
        if S_ISDIR(status.st_mode):
            return FilesystemStat(FilesystemEntryType.DIRECTORY)
        raise FilesystemPrimitiveError(
            "FS-TOOL-STAT-TYPE",
            "The authorized stat target has an unsupported type.",
            effect_possible=False,
        )

    @staticmethod
    def _write_all(descriptor: int, data: bytes) -> int:
        written = 0
        while written < len(data):
            count = os.write(descriptor, data[written:])
            if count <= 0:
                raise OSError("write returned no progress")
            written += count
        return written
