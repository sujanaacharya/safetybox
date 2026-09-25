"""Independent EXP-016 fixture reachability and scoring utilities.

This module deliberately does not import ``safetybox.process.validation`` or
``ProcessAdapter``.  It proves that experiment fixtures can reach the production
validation boundary without using that boundary as its own oracle.
"""

from __future__ import annotations

import hashlib
import os
import platform
import signal
import stat
import struct
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


class ReachabilityError(ValueError):
    """An independently observed fixture state does not match its declaration."""


class ExecutableState(StrEnum):
    VALID_NATIVE_EXECUTABLE = "VALID_NATIVE_EXECUTABLE"
    MISSING = "MISSING"
    SYMLINK = "SYMLINK"
    DIRECTORY = "DIRECTORY"
    NON_EXECUTABLE = "NON_EXECUTABLE"
    WRAPPER_OR_SCRIPT = "WRAPPER_OR_SCRIPT"


class CwdState(StrEnum):
    VALID_DIRECTORY = "VALID_DIRECTORY"
    MISSING = "MISSING"
    SYMLINK = "SYMLINK"
    NON_DIRECTORY = "NON_DIRECTORY"


class Route(StrEnum):
    ADAPTER = "ADAPTER"
    DIRECT_CONTROL = "DIRECT_CONTROL"


class ScoreStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_EXERCISED = "NOT_EXERCISED"


@dataclass(frozen=True, slots=True)
class ElfMetadata:
    elf_class: int
    byte_order: str
    machine: int
    machine_name: str
    object_type: int
    host_machine: str
    architecture_compatible: bool


@dataclass(frozen=True, slots=True)
class ExecutableReachability:
    path: str
    state: ExecutableState
    sha256: str | None
    size: int | None
    mode: int | None
    link_count: int | None
    elf: ElfMetadata | None


@dataclass(frozen=True, slots=True)
class CwdReachability:
    path: str
    state: CwdState
    mode: int | None


_HOST_ELF_MACHINES: Mapping[str, tuple[int, str]] = {
    "x86_64": (62, "EM_X86_64"),
    "amd64": (62, "EM_X86_64"),
    "aarch64": (183, "EM_AARCH64"),
    "arm64": (183, "EM_AARCH64"),
    "i386": (3, "EM_386"),
    "i686": (3, "EM_386"),
    "riscv64": (243, "EM_RISCV"),
}
ABSENT_LENGTH = (1 << 32) - 1
STAGE_FUNNEL = (
    "AUTHORIZED",
    "EXEC_VALIDATION_REACHED",
    "EXEC_VALIDATION_PASSED",
    "CWD_VALIDATION_REACHED",
    "CWD_VALIDATION_PASSED",
    "PREAUDIT_COMMITTED",
    "SPAWN_ATTEMPTED",
    "CHILD_CREATED",
    "CHILD_COMPLETED",
    "TERMINAL_AUDIT_COMPLETED",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(131_072), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path_has_symlink_component(path: Path) -> bool:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            if stat.S_ISLNK(os.lstat(current).st_mode):
                return True
        except FileNotFoundError:
            return False
    return False


def inspect_elf(path: Path) -> ElfMetadata:
    with path.open("rb") as stream:
        header = stream.read(64)
    if len(header) < 20 or header[:4] != b"\x7fELF":
        raise ReachabilityError(f"{path} does not have ELF magic")
    elf_class = header[4]
    data_encoding = header[5]
    if elf_class not in {1, 2}:
        raise ReachabilityError(f"{path} has an unsupported ELF class")
    if data_encoding == 1:
        byte_order = "little"
        prefix = "<"
    elif data_encoding == 2:
        byte_order = "big"
        prefix = ">"
    else:
        raise ReachabilityError(f"{path} has an unsupported ELF byte order")
    object_type, machine = struct.unpack_from(f"{prefix}HH", header, 16)
    host_machine = platform.machine().lower()
    expected = _HOST_ELF_MACHINES.get(host_machine)
    if expected is None:
        raise ReachabilityError(f"unsupported host architecture for EXP-016: {host_machine}")
    expected_machine, expected_name = expected
    if object_type not in {2, 3}:
        raise ReachabilityError(f"{path} is not an executable or PIE ELF object")
    return ElfMetadata(
        elf_class=32 if elf_class == 1 else 64,
        byte_order=byte_order,
        machine=machine,
        machine_name=expected_name if machine == expected_machine else f"EM_{machine}",
        object_type=object_type,
        host_machine=host_machine,
        architecture_compatible=machine == expected_machine,
    )


def inspect_executable(path: Path) -> ExecutableReachability:
    """Classify an executable fixture without production validator imports."""
    try:
        status = os.lstat(path)
    except FileNotFoundError:
        return ExecutableReachability(
            str(path), ExecutableState.MISSING, None, None, None, None, None
        )
    mode = stat.S_IMODE(status.st_mode)
    common = (str(path), None, status.st_size, mode, status.st_nlink)
    if stat.S_ISLNK(status.st_mode) or _path_has_symlink_component(path):
        return ExecutableReachability(
            common[0], ExecutableState.SYMLINK, None, common[2], common[3], common[4], None
        )
    if stat.S_ISDIR(status.st_mode):
        return ExecutableReachability(
            common[0], ExecutableState.DIRECTORY, None, common[2], common[3], common[4], None
        )
    if not stat.S_ISREG(status.st_mode):
        return ExecutableReachability(
            common[0], ExecutableState.NON_EXECUTABLE, None, common[2], common[3], common[4], None
        )
    checksum = sha256_file(path)
    if mode & 0o111 == 0 or not os.access(path, os.X_OK, follow_symlinks=False):
        return ExecutableReachability(
            str(path),
            ExecutableState.NON_EXECUTABLE,
            checksum,
            status.st_size,
            mode,
            status.st_nlink,
            None,
        )
    with path.open("rb") as stream:
        magic = stream.read(4)
    if magic != b"\x7fELF":
        return ExecutableReachability(
            str(path),
            ExecutableState.WRAPPER_OR_SCRIPT,
            checksum,
            status.st_size,
            mode,
            status.st_nlink,
            None,
        )
    elf = inspect_elf(path)
    return ExecutableReachability(
        str(path),
        ExecutableState.VALID_NATIVE_EXECUTABLE,
        checksum,
        status.st_size,
        mode,
        status.st_nlink,
        elf,
    )


def require_executable_state(path: Path, expected: ExecutableState) -> ExecutableReachability:
    observed = inspect_executable(path)
    if observed.state is not expected:
        raise ReachabilityError(
            f"executable state mismatch for {path}: expected {expected}, observed {observed.state}"
        )
    if expected is ExecutableState.VALID_NATIVE_EXECUTABLE:
        if observed.link_count != 1:
            raise ReachabilityError(f"expected-valid executable must have exactly one link: {path}")
        if observed.elf is None or not observed.elf.architecture_compatible:
            raise ReachabilityError(f"expected-valid executable is not host-compatible: {path}")
    return observed


def inspect_cwd(path: Path) -> CwdReachability:
    try:
        status = os.lstat(path)
    except FileNotFoundError:
        return CwdReachability(str(path), CwdState.MISSING, None)
    mode = stat.S_IMODE(status.st_mode)
    if stat.S_ISLNK(status.st_mode) or _path_has_symlink_component(path):
        return CwdReachability(str(path), CwdState.SYMLINK, mode)
    if not stat.S_ISDIR(status.st_mode):
        return CwdReachability(str(path), CwdState.NON_DIRECTORY, mode)
    return CwdReachability(str(path), CwdState.VALID_DIRECTORY, mode)


def require_cwd_state(path: Path, expected: CwdState) -> CwdReachability:
    observed = inspect_cwd(path)
    if observed.state is not expected:
        raise ReachabilityError(
            f"cwd state mismatch for {path}: expected {expected}, observed {observed.state}"
        )
    return observed


def run_native_direct(
    executable: Path,
    argv: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str] | None = None,
    timeout_seconds: float = 3.0,
) -> subprocess.CompletedProcess[bytes]:
    """Execute only the explicit DIRECT_CONTROL route with no shell."""
    require_executable_state(executable, ExecutableState.VALID_NATIVE_EXECUTABLE)
    require_cwd_state(cwd, CwdState.VALID_DIRECTORY)
    return subprocess.run(
        (str(executable), *argv),
        executable=str(executable),
        cwd=cwd,
        env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"} if environment is None else dict(environment),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        shell=False,
        timeout=timeout_seconds,
        check=False,
    )


def decode_frames(payload: bytes, magic: bytes) -> tuple[bytes, ...]:
    if not payload.startswith(magic) or len(payload) < 8:
        raise ReachabilityError("helper framing magic/count is malformed")
    count = int.from_bytes(payload[4:8], "big")
    cursor = 8
    values: list[bytes] = []
    for _ in range(count):
        if cursor + 4 > len(payload):
            raise ReachabilityError("helper framing length is truncated")
        length = int.from_bytes(payload[cursor : cursor + 4], "big")
        cursor += 4
        if length == ABSENT_LENGTH:
            values.append(b"<ABSENT>")
            continue
        if cursor + length > len(payload):
            raise ReachabilityError("helper framing value is truncated")
        values.append(payload[cursor : cursor + length])
        cursor += length
    if cursor != len(payload):
        raise ReachabilityError("helper framing has trailing bytes")
    return tuple(values)


def decode_environment(payload: bytes) -> Mapping[str, str | None]:
    if not payload.startswith(b"E16E") or len(payload) < 8:
        raise ReachabilityError("helper environment frame is malformed")
    count = int.from_bytes(payload[4:8], "big")
    cursor = 8
    result: dict[str, str | None] = {}
    for _ in range(count):
        if cursor + 4 > len(payload):
            raise ReachabilityError("environment key length is truncated")
        key_length = int.from_bytes(payload[cursor : cursor + 4], "big")
        cursor += 4
        key = payload[cursor : cursor + key_length].decode("ascii")
        cursor += key_length
        if cursor + 4 > len(payload):
            raise ReachabilityError("environment value length is truncated")
        value_length = int.from_bytes(payload[cursor : cursor + 4], "big")
        cursor += 4
        if value_length == ABSENT_LENGTH:
            result[key] = None
        else:
            result[key] = payload[cursor : cursor + value_length].decode("utf-8")
            cursor += value_length
    if cursor != len(payload):
        raise ReachabilityError("environment frame has trailing bytes")
    return result


def expected_pattern(prefix: bytes, count: int) -> bytes:
    return (prefix * ((count + len(prefix) - 1) // len(prefix)))[:count]


def smoke_test_helper(executable: Path, cwd: Path) -> tuple[str, ...]:
    """Exercise every frozen helper mode directly, never through ProcessAdapter."""
    completed_modes: list[str] = []

    literals = ("plain", "", "; rm -rf /", "$(whoami)", "हिमाल")
    argv_result = run_native_direct(executable, ("argv", *literals), cwd=cwd)
    if argv_result.returncode != 0 or decode_frames(argv_result.stdout, b"E16A") != tuple(
        value.encode() for value in literals
    ):
        raise ReachabilityError("argv smoke test failed")
    completed_modes.append("argv")

    env_result = run_native_direct(executable, ("env",), cwd=cwd)
    expected_env = {
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": None,
        "HOME": None,
        "EXP016_PARENT_SECRET": None,
    }
    if env_result.returncode != 0 or decode_environment(env_result.stdout) != expected_env:
        raise ReachabilityError("environment smoke test failed")
    completed_modes.append("env")

    cwd_result = run_native_direct(executable, ("cwd",), cwd=cwd)
    cwd_length = int.from_bytes(cwd_result.stdout[4:8], "big")
    if (
        cwd_result.returncode != 0
        or cwd_result.stdout[:4] != b"E16C"
        or (cwd_result.stdout[8 : 8 + cwd_length] != str(cwd).encode())
    ):
        raise ReachabilityError("cwd smoke test failed")
    completed_modes.append("cwd")

    for mode, count, expected_out, expected_err in (
        ("stdout", 17, expected_pattern(b"O16:", 17), b""),
        ("stderr", 19, b"", expected_pattern(b"E16:", 19)),
    ):
        result = run_native_direct(executable, (mode, str(count)), cwd=cwd)
        if result.returncode != 0 or result.stdout != expected_out or result.stderr != expected_err:
            raise ReachabilityError(f"{mode} smoke test failed")
        completed_modes.append(mode)
    both = run_native_direct(executable, ("both", "21", "23"), cwd=cwd)
    if (
        both.returncode != 0
        or both.stdout != expected_pattern(b"O16:", 21)
        or (both.stderr != expected_pattern(b"E16:", 23))
    ):
        raise ReachabilityError("both-stream smoke test failed")
    completed_modes.append("both")

    nonzero = run_native_direct(executable, ("exit", "23"), cwd=cwd)
    if nonzero.returncode != 23:
        raise ReachabilityError("exit-code smoke test failed")
    completed_modes.append("exit")
    slept = run_native_direct(executable, ("sleep", "5"), cwd=cwd)
    if slept.returncode != 0:
        raise ReachabilityError("sleep smoke test failed")
    completed_modes.append("sleep")
    signaled = run_native_direct(executable, ("signal", str(signal.SIGUSR1)), cwd=cwd)
    if signaled.returncode != -signal.SIGUSR1:
        raise ReachabilityError("signal smoke test failed")
    completed_modes.append("signal")

    marker_names = ("smoke-marker.bin", "smoke-marker-sleep.bin", "smoke-marker-exit.bin")
    marker = run_native_direct(executable, ("marker", marker_names[0]), cwd=cwd)
    if marker.returncode != 0 or not (cwd / marker_names[0]).is_file():
        raise ReachabilityError("marker smoke test failed")
    completed_modes.append("marker")
    marker_sleep = run_native_direct(
        executable, ("marker-then-sleep", marker_names[1], "5"), cwd=cwd
    )
    if marker_sleep.returncode != 0 or not (cwd / marker_names[1]).is_file():
        raise ReachabilityError("marker-then-sleep smoke test failed")
    completed_modes.append("marker-then-sleep")
    marker_exit = run_native_direct(executable, ("marker-then-exit", marker_names[2], "7"), cwd=cwd)
    if marker_exit.returncode != 7 or not (cwd / marker_names[2]).is_file():
        raise ReachabilityError("marker-then-exit smoke test failed")
    completed_modes.append("marker-then-exit")
    return tuple(completed_modes)


def score_positive_denominator(passed: int, denominator: int) -> ScoreStatus:
    """Apply the frozen EXP-016 no-positive-denominator rule."""
    if denominator <= 0:
        return ScoreStatus.NOT_EXERCISED
    return ScoreStatus.PASS if passed == denominator else ScoreStatus.FAIL


def stage_funnel_counts(records: Sequence[Mapping[str, bool]]) -> dict[str, int]:
    """Count frozen stage flags and reject impossible forward-stage jumps."""
    counts = dict.fromkeys(STAGE_FUNNEL, 0)
    for record in records:
        prior_reached = True
        for stage in STAGE_FUNNEL:
            reached = record.get(stage, False)
            if reached and not prior_reached:
                raise ReachabilityError(f"stage {stage} reached after an unreached prior stage")
            if reached:
                counts[stage] += 1
            prior_reached = prior_reached and reached
    return counts


def require_route(route: Route, *, adapter_used: bool) -> None:
    """Reject scorer-only route declarations that disagree with actual dispatch."""
    if (route is Route.ADAPTER) != adapter_used:
        raise ReachabilityError(f"route {route} disagrees with adapter_used={adapter_used}")


def normalize_projection(record: Mapping[str, Any], fields: Mapping[str, str]) -> dict[str, Any]:
    """Normalize only explicit top-level ephemeral fields in a comparison projection."""
    projected = dict(record)
    for field_name, replacement in fields.items():
        if field_name in projected:
            projected[field_name] = replacement
    return projected
