"""The only production subprocess-creation boundary for PMED-L1."""

from __future__ import annotations

import hashlib
import subprocess
import threading
from dataclasses import dataclass, field
from io import BufferedReader
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from safetybox.process.errors import ProcessIndeterminateError
from safetybox.process.models import CaptureStatus, StreamMetadata

OUTPUT_RETURN_LIMIT = 65_536
TIMEOUT_GRACE_SECONDS = 0.250
FIXED_CHILD_ENVIRONMENT = {"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}


class _Digest(Protocol):
    def update(self, value: bytes) -> None: ...

    def hexdigest(self) -> str: ...


@dataclass(frozen=True, slots=True)
class SpawnInvocation:
    executable: str
    argv: tuple[str, ...]
    cwd: Path
    environment: tuple[tuple[str, str], ...]
    timeout_ms: int


@dataclass(frozen=True, slots=True)
class ProcessObservation:
    child_created: bool | None
    child_token: str | None = None
    pid: int | None = None
    returncode: int | None = None
    timed_out: bool = False
    term_sent: bool = False
    kill_sent: bool = False
    stdout: bytes | None = None
    stderr: bytes | None = None
    stdout_metadata: StreamMetadata = StreamMetadata(None, None, False, CaptureStatus.NOT_ATTEMPTED)
    stderr_metadata: StreamMetadata = StreamMetadata(None, None, False, CaptureStatus.NOT_ATTEMPTED)

    @property
    def exit_code(self) -> int | None:
        return self.returncode if self.returncode is not None and self.returncode >= 0 else None

    @property
    def signal(self) -> int | None:
        return -self.returncode if self.returncode is not None and self.returncode < 0 else None


@dataclass(slots=True)
class _StreamCollector:
    retained: bytearray = field(default_factory=bytearray)
    byte_count: int = 0
    digest: _Digest = field(default_factory=hashlib.sha256)
    error: Exception | None = None

    def drain(self, stream: BufferedReader) -> None:
        try:
            while True:
                chunk = stream.read(8192)
                if not chunk:
                    return
                self.byte_count += len(chunk)
                self.digest.update(chunk)
                remaining = OUTPUT_RETURN_LIMIT - len(self.retained)
                if remaining > 0:
                    self.retained.extend(chunk[:remaining])
        except Exception as error:
            self.error = error

    def metadata(self) -> StreamMetadata:
        return StreamMetadata(
            self.byte_count,
            self.digest.hexdigest(),
            self.byte_count > OUTPUT_RETURN_LIMIT,
            CaptureStatus.COMPLETE,
        )


@dataclass(slots=True)
class RealProcessPrimitive:
    """Create, observe, terminate, and reap one direct child."""

    invocations: list[SpawnInvocation] = field(default_factory=list, init=False)

    @property
    def invocation_count(self) -> int:
        return len(self.invocations)

    def spawn_and_wait(
        self,
        *,
        executable: str,
        argv: tuple[str, ...],
        cwd: Path,
        timeout_ms: int,
    ) -> ProcessObservation:
        invocation = SpawnInvocation(
            executable,
            argv,
            cwd,
            tuple(sorted(FIXED_CHILD_ENVIRONMENT.items())),
            timeout_ms,
        )
        self.invocations.append(invocation)
        child_token = str(uuid4())
        try:
            child = subprocess.Popen(
                (executable, *argv),
                executable=executable,
                cwd=cwd,
                env=dict(FIXED_CHILD_ENVIRONMENT),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                close_fds=True,
            )
        except OSError as error:
            raise ProcessIndeterminateError(
                "PROC-SPAWN-INDETERMINATE",
                "The process primitive could not establish whether a child was created.",
                cause=error,
                observation=ProcessObservation(None, child_token),
            ) from error

        timed_out = False
        term_sent = False
        kill_sent = False
        stdout_collector = _StreamCollector()
        stderr_collector = _StreamCollector()
        if child.stdout is None or child.stderr is None:  # pragma: no cover - Popen invariant
            raise RuntimeError("process capture pipes were not created")
        stdout_thread = threading.Thread(
            target=stdout_collector.drain, args=(child.stdout,), daemon=True
        )
        stderr_thread = threading.Thread(
            target=stderr_collector.drain, args=(child.stderr,), daemon=True
        )
        stdout_thread.start()
        stderr_thread.start()
        try:
            try:
                child.wait(timeout=timeout_ms / 1000)
            except subprocess.TimeoutExpired:
                timed_out = True
                if child.poll() is None:
                    child.terminate()
                    term_sent = True
                try:
                    child.wait(timeout=TIMEOUT_GRACE_SECONDS)
                except subprocess.TimeoutExpired:
                    if child.poll() is None:
                        child.kill()
                        kill_sent = True
                    child.wait()
            stdout_thread.join(TIMEOUT_GRACE_SECONDS)
            stderr_thread.join(TIMEOUT_GRACE_SECONDS)
            if stdout_thread.is_alive() or stderr_thread.is_alive():
                child.stdout.close()
                child.stderr.close()
                stdout_thread.join(TIMEOUT_GRACE_SECONDS)
                stderr_thread.join(TIMEOUT_GRACE_SECONDS)
                raise OSError("output capture did not reach end-of-stream")
            if stdout_collector.error is not None or stderr_collector.error is not None:
                raise OSError("output capture failed")
        except Exception as error:
            if child.poll() is None:
                try:
                    child.kill()
                    kill_sent = True
                    child.wait()
                except Exception:
                    pass
            observation = ProcessObservation(
                True,
                child_token,
                child.pid,
                child.returncode,
                timed_out,
                term_sent,
                kill_sent,
                stdout_metadata=StreamMetadata(None, None, False, CaptureStatus.FAILED),
                stderr_metadata=StreamMetadata(None, None, False, CaptureStatus.FAILED),
            )
            raise ProcessIndeterminateError(
                "PROC-CAPTURE-INDETERMINATE",
                "Direct-child output or terminal state could not be captured reliably.",
                cause=error,
                observation=observation,
            ) from error

        return ProcessObservation(
            True,
            child_token,
            child.pid,
            child.returncode,
            timed_out,
            term_sent,
            kill_sent,
            bytes(stdout_collector.retained),
            bytes(stderr_collector.retained),
            stdout_collector.metadata(),
            stderr_collector.metadata(),
        )
