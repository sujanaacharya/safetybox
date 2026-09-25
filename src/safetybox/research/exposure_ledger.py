"""Durable, tamper-evident prediction-exposure accounting.

``AUTH-COVERAGE-EXPOSURE-LEDGER@1`` is a small research-governance
instrument.  It provides cooperative one-shot enforcement, reproducibility,
and detection of accidental or after-the-fact modification.  It is not a
security boundary against a privileged attacker: an attacker able to replace
the ledger and every separately stored head/count anchor can rewrite history.

Each append holds an advisory exclusive file lock, validates the complete
existing chain and state machine, writes one canonical JSON line through an
``O_APPEND`` file descriptor, flushes it, and calls ``fsync``.  The directory
entry is also synced when the ledger is first created.  Readers take a shared
lock.  These locks coordinate participating processes on platforms providing
``fcntl.flock``; they do not constrain non-cooperating writers.

The frozen event digest is::

    SHA256(ASCII(previous_digest) || UTF8(canonical_event_json))

Canonical JSON is UTF-8, key-sorted, compact, Unicode-preserving, and rejects
NaN/infinity.  The all-zero SHA-256 value is the genesis previous digest.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import secrets
import tempfile
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import TypeAlias, cast

LEDGER_VERSION = "AUTH-COVERAGE-EXPOSURE-LEDGER@1"
GENESIS_DIGEST = "0" * 64

JSONValue: TypeAlias = str | int | bool | None | list["JSONValue"] | dict[str, "JSONValue"]


class ExposureLedgerError(ValueError):
    """Base class for invalid ledger operations."""


class ExposureLedgerIntegrityError(ExposureLedgerError):
    """The persisted ledger is malformed, corrupt, or semantically invalid."""


class DuplicateExposureError(ExposureLedgerError):
    """A token or scenario would be reserved or exposed more than once."""


class ExposureBindingError(ExposureLedgerError):
    """An event does not match the binding established by its reservation."""


class ExposureTransitionError(ExposureLedgerError):
    """An event is not legal from the token's current state."""


class ExposurePresentError(ExposureLedgerError):
    """A zero-exposure gate found prior prediction exposure."""


class ExposureEventType(StrEnum):
    RESERVED = "RESERVED"
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED_AFTER_CALL = "FAILED_AFTER_CALL"
    FAILED_BEFORE_CALL = "FAILED_BEFORE_CALL"
    ABORTED_BEFORE_CALL = "ABORTED_BEFORE_CALL"
    RECONCILED = "RECONCILED"


@dataclass(frozen=True, slots=True)
class ExposureBinding:
    """Fields to which one single-use exposure token is permanently bound."""

    experiment_id: str
    corpus_id: str
    split: str
    run_id: str
    scenario_id: str
    component: str
    implementation_sha: str
    token: str

    def __post_init__(self) -> None:
        for name, value in self.to_dict().items():
            if not isinstance(value, str) or not value:
                raise ExposureBindingError(f"{name} must be a non-empty string")

    def to_dict(self) -> dict[str, str]:
        return {
            "component": self.component,
            "corpus_id": self.corpus_id,
            "experiment_id": self.experiment_id,
            "implementation_sha": self.implementation_sha,
            "run_id": self.run_id,
            "scenario_id": self.scenario_id,
            "split": self.split,
            "token": self.token,
        }

    @classmethod
    def from_dict(cls, value: object) -> ExposureBinding:
        if not isinstance(value, dict):
            raise ExposureLedgerIntegrityError("event binding must be an object")
        expected = {
            "component",
            "corpus_id",
            "experiment_id",
            "implementation_sha",
            "run_id",
            "scenario_id",
            "split",
            "token",
        }
        if set(value) != expected or any(not isinstance(item, str) for item in value.values()):
            raise ExposureLedgerIntegrityError("event binding has invalid fields")
        typed = cast(dict[str, str], value)
        try:
            return cls(**typed)
        except ExposureBindingError as error:
            raise ExposureLedgerIntegrityError(str(error)) from error


@dataclass(frozen=True, slots=True)
class ExposureEvent:
    sequence: int
    event_type: ExposureEventType
    binding: ExposureBinding
    timestamp: str
    details: dict[str, JSONValue]

    def to_dict(self) -> dict[str, JSONValue]:
        return {
            "binding": cast(dict[str, JSONValue], self.binding.to_dict()),
            "details": self.details,
            "event_type": self.event_type.value,
            "sequence": self.sequence,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, value: object) -> ExposureEvent:
        if not isinstance(value, dict):
            raise ExposureLedgerIntegrityError("event must be an object")
        if set(value) != {"binding", "details", "event_type", "sequence", "timestamp"}:
            raise ExposureLedgerIntegrityError("event has invalid fields")
        sequence = value["sequence"]
        timestamp = value["timestamp"]
        details = value["details"]
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence <= 0:
            raise ExposureLedgerIntegrityError("event sequence must be a positive integer")
        if not isinstance(timestamp, str) or not timestamp:
            raise ExposureLedgerIntegrityError("event timestamp must be a non-empty string")
        if not isinstance(details, dict) or any(not isinstance(key, str) for key in details):
            raise ExposureLedgerIntegrityError("event details must be an object with string keys")
        try:
            _canonical_json(details)
        except ExposureLedgerError as error:
            raise ExposureLedgerIntegrityError("event details are not canonical JSON") from error
        try:
            event_type = ExposureEventType(value["event_type"])
        except (TypeError, ValueError) as error:
            raise ExposureLedgerIntegrityError("unknown exposure event type") from error
        return cls(
            sequence=sequence,
            event_type=event_type,
            binding=ExposureBinding.from_dict(value["binding"]),
            timestamp=timestamp,
            details=cast(dict[str, JSONValue], details),
        )


@dataclass(frozen=True, slots=True)
class LedgerIntegrity:
    valid: bool
    event_count: int
    head: str
    errors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _VerifiedLedger:
    events: tuple[ExposureEvent, ...]
    head: str


def new_exposure_token() -> str:
    """Return a cryptographically random 256-bit token."""
    return secrets.token_hex(32)


def canonical_json(value: Mapping[str, JSONValue]) -> bytes:
    """Return the frozen canonical JSON representation used by the ledger."""
    return _canonical_json(dict(value))


def event_digest(previous_digest: str, event: ExposureEvent) -> str:
    """Compute the frozen chain digest for an event."""
    if not _is_sha256(previous_digest):
        raise ExposureLedgerError("previous_digest must be a lowercase SHA-256 digest")
    return hashlib.sha256(
        previous_digest.encode("ascii") + _canonical_json(event.to_dict())
    ).hexdigest()


class ExposureLedger:
    """Append-only file ledger with durable single-use exposure reservations."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.anchor_path = self.path.with_name(f"{self.path.name}.anchor.json")

    def reserve(
        self,
        binding: ExposureBinding,
        *,
        timestamp: str | None = None,
        details: Mapping[str, JSONValue] | None = None,
    ) -> ExposureEvent:
        if binding.split == "HELD_OUT":
            raise ExposureBindingError(
                "HELD_OUT reservations require atomic canonical-scope enforcement"
            )
        return self._append(ExposureEventType.RESERVED, binding, timestamp, details)

    def reserve_canonical_scope(
        self,
        binding: ExposureBinding,
        *,
        timestamp: str | None = None,
        details: Mapping[str, JSONValue] | None = None,
    ) -> ExposureEvent:
        """Atomically bind one held-out corpus scope to its first canonical run."""
        if binding.split != "HELD_OUT":
            raise ExposureBindingError("canonical-scope reservation requires HELD_OUT")
        return self._append(
            ExposureEventType.RESERVED,
            binding,
            timestamp,
            details,
            canonical_scope=True,
        )

    def mark_started(
        self,
        binding: ExposureBinding,
        *,
        timestamp: str | None = None,
        details: Mapping[str, JSONValue] | None = None,
    ) -> ExposureEvent:
        """Durably mark possible exposure immediately before the production call."""
        return self._append(ExposureEventType.STARTED, binding, timestamp, details)

    def complete(
        self,
        binding: ExposureBinding,
        *,
        timestamp: str | None = None,
        details: Mapping[str, JSONValue] | None = None,
    ) -> ExposureEvent:
        return self._append(ExposureEventType.COMPLETED, binding, timestamp, details)

    def fail_after_call(
        self,
        binding: ExposureBinding,
        *,
        timestamp: str | None = None,
        details: Mapping[str, JSONValue] | None = None,
    ) -> ExposureEvent:
        return self._append(ExposureEventType.FAILED_AFTER_CALL, binding, timestamp, details)

    def fail_before_call(
        self,
        binding: ExposureBinding,
        *,
        timestamp: str | None = None,
        details: Mapping[str, JSONValue] | None = None,
    ) -> ExposureEvent:
        return self._append(ExposureEventType.FAILED_BEFORE_CALL, binding, timestamp, details)

    def abort_before_call(
        self,
        binding: ExposureBinding,
        *,
        timestamp: str | None = None,
        details: Mapping[str, JSONValue] | None = None,
    ) -> ExposureEvent:
        return self._append(ExposureEventType.ABORTED_BEFORE_CALL, binding, timestamp, details)

    def reconcile(
        self,
        binding: ExposureBinding,
        *,
        status: str,
        timestamp: str | None = None,
        details: Mapping[str, JSONValue] | None = None,
    ) -> ExposureEvent:
        if not status:
            raise ExposureLedgerError("reconciliation status must be non-empty")
        merged: dict[str, JSONValue] = dict(details or {})
        if "status" in merged:
            raise ExposureLedgerError("reconciliation details cannot override status")
        merged["status"] = status
        return self._append(ExposureEventType.RECONCILED, binding, timestamp, merged)

    def events(self) -> tuple[ExposureEvent, ...]:
        if not self.path.exists():
            _verify_anchor(self.anchor_path, _VerifiedLedger((), GENESIS_DIGEST))
            return ()
        with self.path.open("rb") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_SH)
            data = stream.read()
            verified = _verify_bytes(data)
            _verify_anchor(self.anchor_path, verified)
            return verified.events

    @property
    def event_count(self) -> int:
        return len(self.events())

    @property
    def head(self) -> str:
        if not self.path.exists():
            _verify_anchor(self.anchor_path, _VerifiedLedger((), GENESIS_DIGEST))
            return GENESIS_DIGEST
        with self.path.open("rb") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_SH)
            verified = _verify_bytes(stream.read())
            _verify_anchor(self.anchor_path, verified)
            return verified.head

    def verify_integrity(
        self, *, expected_head: str | None = None, expected_event_count: int | None = None
    ) -> LedgerIntegrity:
        try:
            if not self.path.exists():
                verified = _VerifiedLedger((), GENESIS_DIGEST)
                _verify_anchor(self.anchor_path, verified)
            else:
                with self.path.open("rb") as stream:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_SH)
                    verified = _verify_bytes(stream.read())
                    _verify_anchor(self.anchor_path, verified)
            errors: list[str] = []
            if expected_head is not None and verified.head != expected_head:
                errors.append("ledger head differs from expected anchor")
            if expected_event_count is not None and len(verified.events) != expected_event_count:
                errors.append("ledger event count differs from expected anchor")
            return LedgerIntegrity(
                valid=not errors,
                event_count=len(verified.events),
                head=verified.head,
                errors=tuple(errors),
            )
        except ExposureLedgerIntegrityError as error:
            return LedgerIntegrity(False, 0, GENESIS_DIGEST, (str(error),))

    def snapshot_to(self, path: str | Path) -> ExposureLedger:
        """Create or verify an immutable point-in-time ledger copy.

        The source bytes and durable head/count anchor are read while holding the
        ledger's shared lock, so a cooperating append cannot be split across the
        snapshot.  Existing snapshot files must match byte-for-byte.
        """
        destination = ExposureLedger(path)
        if destination.path.resolve() == self.path.resolve():
            raise ExposureLedgerError("ledger snapshot destination must be distinct")
        if self.path.exists():
            with self.path.open("rb") as stream:
                fcntl.flock(stream.fileno(), fcntl.LOCK_SH)
                ledger_bytes = stream.read()
                verified = _verify_bytes(ledger_bytes)
                _verify_anchor(self.anchor_path, verified)
        else:
            ledger_bytes = b""
            verified = _VerifiedLedger((), GENESIS_DIGEST)
            _verify_anchor(self.anchor_path, verified)
        if destination.path.exists():
            snapshot_bytes = destination.path.read_bytes()
            snapshot_verified = _verify_bytes(snapshot_bytes)
            _verify_anchor(destination.anchor_path, snapshot_verified)
            if not ledger_bytes.startswith(snapshot_bytes):
                raise ExposureLedgerIntegrityError(
                    "existing ledger snapshot is not a prefix of live history"
                )
            return destination
        if destination.anchor_path.exists():
            raise ExposureLedgerIntegrityError("snapshot anchor exists without its ledger")
        destination.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            destination.path,
            os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        try:
            _fsync_directory(destination.path.parent)
            _write_anchor(
                destination.anchor_path,
                head=GENESIS_DIGEST,
                event_count=0,
            )
            with os.fdopen(descriptor, "ab", closefd=True) as stream:
                stream.write(ledger_bytes)
                stream.flush()
                os.fsync(stream.fileno())
            _write_anchor(
                destination.anchor_path,
                head=verified.head,
                event_count=len(verified.events),
            )
        except BaseException:
            try:
                os.close(descriptor)
            except OSError:
                pass
            raise
        integrity = destination.verify_integrity(
            expected_head=verified.head,
            expected_event_count=len(verified.events),
        )
        if not integrity.valid:
            raise ExposureLedgerIntegrityError("ledger snapshot failed integrity verification")
        return destination

    def prediction_exposure_count(
        self,
        *,
        experiment_id: str,
        split: str,
        corpus_id: str | None = None,
        component: str | None = None,
    ) -> int:
        return sum(
            event.event_type is ExposureEventType.STARTED
            and _matches(event.binding, experiment_id, split, corpus_id, component)
            for event in self.events()
        )

    def scenario_exposed(self, binding: ExposureBinding) -> bool:
        return any(
            event.event_type is ExposureEventType.STARTED
            and _scenario_key(event.binding) == _scenario_key(binding)
            for event in self.events()
        )

    def run_has_exposure(self, *, experiment_id: str, run_id: str) -> bool:
        return any(
            event.event_type is ExposureEventType.STARTED
            and event.binding.experiment_id == experiment_id
            and event.binding.run_id == run_id
            for event in self.events()
        )

    def duplicate_exposure_count(self) -> int:
        keys = [
            _scenario_key(event.binding)
            for event in self.events()
            if event.event_type is ExposureEventType.STARTED
        ]
        return sum(count - 1 for count in Counter(keys).values() if count > 1)

    def incomplete_exposure_count(
        self, *, experiment_id: str | None = None, run_id: str | None = None
    ) -> int:
        started: set[str] = set()
        complete: set[str] = set()
        for event in self.events():
            binding = event.binding
            if experiment_id is not None and binding.experiment_id != experiment_id:
                continue
            if run_id is not None and binding.run_id != run_id:
                continue
            if event.event_type is ExposureEventType.STARTED:
                started.add(binding.token)
            elif event.event_type is ExposureEventType.COMPLETED:
                complete.add(binding.token)
        return len(started - complete)

    def require_zero_exposure(
        self, *, experiment_id: str, corpus_id: str, split: str, component: str
    ) -> None:
        count = self.prediction_exposure_count(
            experiment_id=experiment_id,
            corpus_id=corpus_id,
            split=split,
            component=component,
        )
        if count:
            raise ExposurePresentError(
                "zero-exposure gate rejected execution: "
                f"{count} prior exposure(s) for exact experiment/corpus/split/component"
            )

    def _append(
        self,
        event_type: ExposureEventType,
        binding: ExposureBinding,
        timestamp: str | None,
        details: Mapping[str, JSONValue] | None,
        *,
        canonical_scope: bool = False,
    ) -> ExposureEvent:
        normalized_details = dict(details or {})
        _canonical_json(normalized_details)
        event_timestamp = timestamp or _utc_timestamp()
        if not event_timestamp:
            raise ExposureLedgerError("timestamp must be non-empty")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existed = self.path.exists()
        descriptor = os.open(self.path, os.O_RDWR | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            with os.fdopen(descriptor, "r+b", closefd=True) as stream:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
                stream.seek(0)
                verified = _verify_bytes(stream.read())
                _verify_anchor(self.anchor_path, verified)
                if not verified.events and not self.anchor_path.exists():
                    # Establish a durable genesis prefix before the first event.
                    # If the event fsync wins but its anchor update is interrupted,
                    # ordinary stale-prefix recovery can advance from this anchor.
                    _write_anchor(
                        self.anchor_path,
                        head=GENESIS_DIGEST,
                        event_count=0,
                    )
                event = ExposureEvent(
                    sequence=len(verified.events) + 1,
                    event_type=event_type,
                    binding=binding,
                    timestamp=event_timestamp,
                    details=normalized_details,
                )
                if canonical_scope:
                    scope_events = [
                        prior
                        for prior in verified.events
                        if prior.binding.experiment_id == binding.experiment_id
                        and prior.binding.corpus_id == binding.corpus_id
                        and prior.binding.split == binding.split
                        and prior.binding.component == binding.component
                    ]
                    if any(prior.binding.run_id != binding.run_id for prior in scope_events):
                        raise ExposurePresentError(
                            "held-out corpus scope is already bound to another run"
                        )
                    if any(
                        prior.binding.scenario_id == binding.scenario_id
                        for prior in scope_events
                    ):
                        raise DuplicateExposureError(
                            "held-out scenario already has a canonical reservation"
                        )
                _validate_next(verified.events, event)
                digest = event_digest(verified.head, event)
                envelope: dict[str, JSONValue] = {
                    "event": event.to_dict(),
                    "event_digest": digest,
                    "ledger_version": LEDGER_VERSION,
                    "previous_digest": verified.head,
                }
                stream.seek(0, os.SEEK_END)
                stream.write(_canonical_json(envelope) + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
                if not existed:
                    _fsync_directory(self.path.parent)
                _write_anchor(
                    self.anchor_path,
                    head=digest,
                    event_count=len(verified.events) + 1,
                )
                return event
        except BaseException:
            # os.fdopen owns descriptor after successful construction, but not if it failed.
            try:
                os.close(descriptor)
            except OSError:
                pass
            raise


def prediction_exposure_count(
    ledger: ExposureLedger,
    *,
    experiment_id: str,
    split: str,
    corpus_id: str | None = None,
    component: str | None = None,
) -> int:
    return ledger.prediction_exposure_count(
        experiment_id=experiment_id,
        split=split,
        corpus_id=corpus_id,
        component=component,
    )


def scenario_exposed(ledger: ExposureLedger, binding: ExposureBinding) -> bool:
    return ledger.scenario_exposed(binding)


def run_has_exposure(ledger: ExposureLedger, *, experiment_id: str, run_id: str) -> bool:
    return ledger.run_has_exposure(experiment_id=experiment_id, run_id=run_id)


def duplicate_exposure_count(ledger: ExposureLedger) -> int:
    return ledger.duplicate_exposure_count()


def incomplete_exposure_count(
    ledger: ExposureLedger, *, experiment_id: str | None = None, run_id: str | None = None
) -> int:
    return ledger.incomplete_exposure_count(experiment_id=experiment_id, run_id=run_id)


def ledger_integrity(
    ledger: ExposureLedger,
    *,
    expected_head: str | None = None,
    expected_event_count: int | None = None,
) -> LedgerIntegrity:
    return ledger.verify_integrity(
        expected_head=expected_head, expected_event_count=expected_event_count
    )


def zero_exposure_gate(
    ledger: ExposureLedger,
    *,
    experiment_id: str,
    corpus_id: str,
    split: str,
    component: str,
) -> None:
    ledger.require_zero_exposure(
        experiment_id=experiment_id,
        corpus_id=corpus_id,
        split=split,
        component=component,
    )


def _canonical_json(value: object) -> bytes:
    _validate_json_value(value)
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ExposureLedgerError("value is not canonical-JSON serializable") from error


def _validate_json_value(value: object) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int):
        return
    if isinstance(value, list):
        for item in value:
            _validate_json_value(item)
        return
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ExposureLedgerError("canonical JSON objects require string keys")
        for item in value.values():
            _validate_json_value(item)
        return
    raise ExposureLedgerError(
        "canonical JSON permits only null, bool, int, string, arrays, objects"
    )


def _verify_bytes(data: bytes) -> _VerifiedLedger:
    if not data:
        return _VerifiedLedger((), GENESIS_DIGEST)
    if not data.endswith(b"\n"):
        raise ExposureLedgerIntegrityError("ledger ends with an incomplete record")
    previous = GENESIS_DIGEST
    events: list[ExposureEvent] = []
    for line_number, line in enumerate(data.splitlines(), start=1):
        try:
            raw = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ExposureLedgerIntegrityError(
                f"ledger line {line_number} is not valid JSON"
            ) from error
        try:
            canonical_line = _canonical_json(raw)
        except ExposureLedgerError as error:
            raise ExposureLedgerIntegrityError(
                f"ledger line {line_number} contains unsupported JSON values"
            ) from error
        if line != canonical_line:
            raise ExposureLedgerIntegrityError(
                f"ledger line {line_number} is not canonically serialized"
            )
        if not isinstance(raw, dict) or set(raw) != {
            "event",
            "event_digest",
            "ledger_version",
            "previous_digest",
        }:
            raise ExposureLedgerIntegrityError(f"ledger line {line_number} has invalid fields")
        if raw["ledger_version"] != LEDGER_VERSION:
            raise ExposureLedgerIntegrityError(f"ledger line {line_number} has wrong version")
        if raw["previous_digest"] != previous:
            raise ExposureLedgerIntegrityError(
                f"ledger line {line_number} previous digest does not match"
            )
        event = ExposureEvent.from_dict(raw["event"])
        if event.sequence != line_number:
            raise ExposureLedgerIntegrityError(
                f"ledger line {line_number} has a non-contiguous sequence"
            )
        digest = event_digest(previous, event)
        if raw["event_digest"] != digest:
            raise ExposureLedgerIntegrityError(f"ledger line {line_number} digest does not match")
        try:
            _validate_next(tuple(events), event)
        except ExposureLedgerError as error:
            raise ExposureLedgerIntegrityError(
                f"ledger line {line_number} violates event semantics: {error}"
            ) from error
        events.append(event)
        previous = digest
    return _VerifiedLedger(tuple(events), previous)


def _validate_next(events: tuple[ExposureEvent, ...], event: ExposureEvent) -> None:
    token_events = [prior for prior in events if prior.binding.token == event.binding.token]
    if event.event_type is ExposureEventType.RESERVED:
        if token_events:
            raise DuplicateExposureError("single-use token has already been reserved")
        if any(_scenario_key(prior.binding) == _scenario_key(event.binding) for prior in events):
            raise DuplicateExposureError("scenario is already reserved in this one-shot run")
        return
    if not token_events:
        raise ExposureTransitionError("event requires a prior durable reservation")
    reserved = token_events[0]
    if reserved.event_type is not ExposureEventType.RESERVED:
        raise ExposureTransitionError("token history does not begin with RESERVED")
    if reserved.binding != event.binding:
        raise ExposureBindingError("token cannot be reused with a different binding")
    types = [prior.event_type for prior in token_events]
    if ExposureEventType.RECONCILED in types:
        raise ExposureTransitionError("reconciled token history is terminal")
    started = ExposureEventType.STARTED in types
    before_terminal = bool(
        {ExposureEventType.FAILED_BEFORE_CALL, ExposureEventType.ABORTED_BEFORE_CALL} & set(types)
    )
    after_terminal = bool(
        {ExposureEventType.COMPLETED, ExposureEventType.FAILED_AFTER_CALL} & set(types)
    )
    if event.event_type is ExposureEventType.STARTED:
        if started or before_terminal or after_terminal:
            raise DuplicateExposureError("single-use token cannot start production twice")
        return
    if event.event_type in {
        ExposureEventType.FAILED_BEFORE_CALL,
        ExposureEventType.ABORTED_BEFORE_CALL,
    }:
        if started or before_terminal or after_terminal:
            raise ExposureTransitionError("before-call terminal event is no longer legal")
        return
    if event.event_type in {
        ExposureEventType.COMPLETED,
        ExposureEventType.FAILED_AFTER_CALL,
    }:
        if not started:
            raise ExposureTransitionError("after-call event requires STARTED")
        if after_terminal:
            raise ExposureTransitionError("call already has a terminal event")
        return
    if event.event_type is ExposureEventType.RECONCILED:
        status = event.details.get("status")
        expected_status: str | None = None
        if before_terminal:
            expected_status = "RESERVED_NOT_EXPOSED"
        elif ExposureEventType.FAILED_AFTER_CALL in types:
            expected_status = "EXPOSED_RAW_MISSING"
        elif ExposureEventType.COMPLETED in types:
            expected_status = "RAW_PRESENT_COMPLETION_EVENT_MISSING"
        if expected_status is None:
            raise ExposureTransitionError("reconciliation requires a terminal call event")
        if status != expected_status:
            raise ExposureTransitionError("reconciliation status differs from call evidence")
        return
    raise ExposureTransitionError("unsupported event transition")


def _scenario_key(binding: ExposureBinding) -> tuple[str, ...]:
    return (
        binding.experiment_id,
        binding.corpus_id,
        binding.split,
        binding.run_id,
        binding.scenario_id,
        binding.component,
    )


def _matches(
    binding: ExposureBinding,
    experiment_id: str,
    split: str,
    corpus_id: str | None,
    component: str | None,
) -> bool:
    return (
        binding.experiment_id == experiment_id
        and binding.split == split
        and (corpus_id is None or binding.corpus_id == corpus_id)
        and (component is None or binding.component == component)
    )


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _verify_anchor(path: Path, verified: _VerifiedLedger) -> None:
    if not path.exists():
        if verified.events:
            raise ExposureLedgerIntegrityError("durable ledger anchor is missing")
        return
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ExposureLedgerIntegrityError("durable ledger anchor is invalid") from error
    expected = {
        "event_count": len(verified.events),
        "head": verified.head,
        "ledger_version": LEDGER_VERSION,
    }
    if value == expected:
        return
    if (
        isinstance(value, dict)
        and value.get("ledger_version") == LEDGER_VERSION
        and isinstance(value.get("event_count"), int)
        and 0 <= value["event_count"] < len(verified.events)
        and isinstance(value.get("head"), str)
    ):
        prefix = GENESIS_DIGEST
        for event in verified.events[: value["event_count"]]:
            prefix = event_digest(prefix, event)
        if prefix == value["head"]:
            # The ledger fsync won and the separately replaced anchor lost a
            # crash race.  Only a valid extension of the anchored prefix may
            # move the anchor forward; truncation and replacement never do.
            _write_anchor(path, head=verified.head, event_count=len(verified.events))
            return
    raise ExposureLedgerIntegrityError("durable ledger anchor does not match history")


def _write_anchor(path: Path, *, head: str, event_count: int) -> None:
    payload = _canonical_json(
        {"event_count": event_count, "head": head, "ledger_version": LEDGER_VERSION}
    ) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()
