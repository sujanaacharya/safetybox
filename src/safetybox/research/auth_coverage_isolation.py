"""Physical/package and import gates for label-blind authorization execution."""

from __future__ import annotations

import importlib.abc
import json
import os
import sys
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any

LABEL_ISOLATION_ID = "AUTH-COVERAGE-002-LABEL-ISOLATION@1"

# Exact research namespaces that the canonical execution interpreter must not load.
PROHIBITED_MODULE_PREFIXES = (
    "safetybox.research.auth_coverage_metrics",
    "safetybox.research.auth_coverage_scoring",
    "auth_coverage_oracle",
    "oracle_a",
    "oracle_b",
)

PROHIBITED_PATH_PARTS = frozenset(
    {
        "analysis",
        "labels",
        "families",
        "pairs",
        "difficulty",
        "oracles",
        "oracle_a.py",
        "oracle_b.py",
        "labels.json",
    }
)

PROHIBITED_RUNTIME_KEYS = frozenset(
    {
        "expected_decision",
        "family",
        "family_label",
        "difficulty",
        "pair_id",
        "oracle_output",
        "authority_distance",
        "error_category",
        "scoring_category",
        "split_derivation",
        "split_derivation_logic",
    }
)


class IsolationViolation(RuntimeError):
    """Raised before execution if analysis information crosses the boundary."""


class _ProhibitedImportFinder(importlib.abc.MetaPathFinder):
    def find_spec(
        self,
        fullname: str,
        path: object = None,
        target: object = None,
    ) -> None:
        del path, target
        if any(
            fullname == prefix or fullname.startswith(f"{prefix}.")
            for prefix in PROHIBITED_MODULE_PREFIXES
        ):
            raise IsolationViolation(f"prohibited execution-process import: {fullname}")
        return None


def assert_prohibited_modules_not_loaded() -> None:
    contaminated = sorted(
        name
        for name in sys.modules
        if any(
            name == prefix or name.startswith(f"{prefix}.")
            for prefix in PROHIBITED_MODULE_PREFIXES
        )
    )
    if contaminated:
        raise IsolationViolation(f"analysis modules already loaded: {contaminated}")


def install_import_gate() -> None:
    """Install the fresh-process import denial gate.

    Call only once, immediately after execution-only imports.  The canonical CLI
    does this in its fresh interpreter before opening the runtime package.
    """
    assert_prohibited_modules_not_loaded()
    if not any(isinstance(finder, _ProhibitedImportFinder) for finder in sys.meta_path):
        sys.meta_path.insert(0, _ProhibitedImportFinder())


def install_file_access_gate(
    *,
    runtime_files: tuple[Path, ...],
    output_root: Path,
    governance_files: tuple[Path, ...],
    implementation_files: tuple[Path, ...],
) -> None:
    """Deny ordinary file access outside runtime, output, and bound source files.

    This is installed only in the fresh canonical process after Python imports
    and package preflight.  It is a cooperative process boundary, not an OS
    sandbox, but it covers ordinary ``open``/``Path.open`` calls mechanically.
    """
    runtime = frozenset(path.resolve(strict=True) for path in runtime_files)
    output = output_root.resolve(strict=True)
    governance = tuple(path.resolve() for path in governance_files)
    governance_directories = frozenset(path.parent for path in governance)
    sources = frozenset(path.resolve(strict=True) for path in implementation_files)

    def within(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
        except ValueError:
            return False
        return True

    def audit(event: str, args: tuple[object, ...]) -> None:
        if event in {"os.listdir", "os.scandir"} and args:
            if not isinstance(args[0], str | bytes | os.PathLike):
                raise IsolationViolation("canonical process denied unknown directory handle")
            candidate = Path(os.fsdecode(args[0])).resolve()
            if within(candidate, runtime_files[0].resolve(strict=True).parent) or within(
                candidate, output
            ):
                return
            raise IsolationViolation(f"canonical process directory access denied: {candidate}")
        if event != "open" or not args or isinstance(args[0], int):
            return
        if not isinstance(args[0], str | bytes | os.PathLike):
            raise IsolationViolation("canonical process denied unknown file handle")
        candidate = Path(os.fsdecode(args[0])).resolve()
        directory_fsync = (
            candidate in governance_directories
            and any(
                isinstance(argument, int)
                and bool(argument & getattr(os, "O_DIRECTORY", 0))
                for argument in args[1:]
            )
        )
        if (
            candidate in runtime
            or within(candidate, output)
            or candidate in governance
            or directory_fsync
            or any(
                candidate.parent == path.parent
                and candidate.name.startswith(f".{path.name}.")
                for path in governance
            )
            or candidate in sources
        ):
            return
        raise IsolationViolation(f"canonical process file access denied: {candidate}")

    sys.addaudithook(audit)


def _walk_keys(value: object) -> Iterator[str]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield str(key).casefold()
            yield from _walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys(item)


def _validate_json_payload(path: Path) -> None:
    suffix = path.suffix.casefold()
    if suffix not in {".json", ".jsonl"}:
        return
    try:
        if suffix == ".jsonl":
            values = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        else:
            values = [json.loads(path.read_text(encoding="utf-8"))]
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise IsolationViolation(f"runtime JSON is not valid: {path}") from error
    keys = {key for value in values for key in _walk_keys(value)}
    leaked = sorted(keys & PROHIBITED_RUNTIME_KEYS)
    if leaked:
        raise IsolationViolation(f"prohibited analysis keys in runtime package: {leaked}")


@dataclass(frozen=True, slots=True)
class RuntimeOnlyPackage:
    """A confined directory that contains execution-visible artifacts only."""

    root: Path

    def validate(self) -> tuple[Path, ...]:
        root = self.root.resolve(strict=True)
        if not root.is_dir():
            raise IsolationViolation("runtime package root must be a directory")
        files: list[Path] = []
        for candidate in sorted(root.rglob("*")):
            relative = candidate.relative_to(root)
            relative_parts = {part.casefold() for part in relative.parts}
            if relative_parts & PROHIBITED_PATH_PARTS:
                message = f"prohibited analysis artifact in runtime package: {relative}"
                raise IsolationViolation(message)
            if candidate.is_symlink():
                raise IsolationViolation(f"runtime package must not contain symlinks: {relative}")
            if candidate.is_file():
                _validate_json_payload(candidate)
                files.append(candidate)
        return tuple(files)

    def validate_exact(self, allowed_files: tuple[Path, ...]) -> tuple[Path, ...]:
        """Require the runtime package to contain exactly the frozen file set."""
        files = self.validate()
        root = self.root.resolve(strict=True)
        expected: set[Path] = set()
        for path in allowed_files:
            resolved = path.resolve(strict=True)
            try:
                resolved.relative_to(root)
            except ValueError as error:
                raise IsolationViolation(
                    "frozen runtime inventory contains a path outside its package"
                ) from error
            expected.add(resolved)
        observed = {path.resolve(strict=True) for path in files}
        if observed != expected:
            unexpected = sorted(str(path.relative_to(root)) for path in observed - expected)
            missing = sorted(str(path.relative_to(root)) for path in expected - observed)
            raise IsolationViolation(
                f"runtime inventory differs from frozen allowlist: "
                f"unexpected={unexpected}, missing={missing}"
            )
        return files

    def open_binary(self, relative_path: str) -> IO[bytes]:
        """Open within the package; traversal and analysis names fail mechanically."""
        root = self.root.resolve(strict=True)
        candidate = (root / relative_path).resolve(strict=True)
        try:
            relative = candidate.relative_to(root)
        except ValueError as error:
            raise IsolationViolation("runtime read attempted outside sealed package") from error
        if {part.casefold() for part in relative.parts} & PROHIBITED_PATH_PARTS:
            raise IsolationViolation("runtime read attempted on an analysis artifact")
        return candidate.open("rb")


def isolation_attestation(runtime_root: Path) -> dict[str, Any]:
    package = RuntimeOnlyPackage(runtime_root)
    files = package.validate()
    assert_prohibited_modules_not_loaded()
    return {
        "isolation_id": LABEL_ISOLATION_ID,
        "runtime_root": str(runtime_root.resolve()),
        "validated_files": [str(path.relative_to(runtime_root.resolve())) for path in files],
        "prohibited_modules_loaded": [],
        "analysis_artifacts_present": False,
    }
