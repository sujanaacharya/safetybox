"""Crash-aware run governance for the AUTH-COVERAGE-002 research instrument.

The state machine is deliberately outside :mod:`safetybox.policy`.  It governs a
benchmark invocation of the public production authorizer; it is not an
authorization rule and must never become one.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields, replace
from enum import StrEnum
from pathlib import Path
from typing import Any

STATE_MACHINE_ID = "AUTH-COVERAGE-002-RUN-STATE-MACHINE@1"
RUN_MANIFEST_ID = "AUTH-COVERAGE-002-RUN-MANIFEST@1"
EXECUTION_PROTOCOL_ID = "AUTH-COVERAGE-002-EXECUTION-PROTOCOL@1"
PRODUCTION_COMPONENT_ID = "TaskContractPolicy.authorize"


class ResearchSplit(StrEnum):
    DEV = "DEV"
    VALIDATION = "VALIDATION"
    HELD_OUT = "HELD_OUT"


class RunState(StrEnum):
    CREATED = "CREATED"
    READY = "READY"
    RUNNING_UNEXPOSED = "RUNNING_UNEXPOSED"
    RUNNING_EXPOSED = "RUNNING_EXPOSED"
    COMPLETED_RAW = "COMPLETED_RAW"
    SEALED_RAW = "SEALED_RAW"
    SCORING = "SCORING"
    COMPLETE = "COMPLETE"
    PARTIAL_AFTER_PREDICTION_EXPOSURE = "PARTIAL_AFTER_PREDICTION_EXPOSURE"
    ABORTED_BEFORE_PREDICTION = "ABORTED_BEFORE_PREDICTION"
    INVALID = "INVALID"


LEGAL_TRANSITIONS: dict[RunState, frozenset[RunState]] = {
    RunState.CREATED: frozenset(
        {RunState.READY, RunState.ABORTED_BEFORE_PREDICTION, RunState.INVALID}
    ),
    RunState.READY: frozenset(
        {RunState.RUNNING_UNEXPOSED, RunState.ABORTED_BEFORE_PREDICTION, RunState.INVALID}
    ),
    RunState.RUNNING_UNEXPOSED: frozenset(
        {
            RunState.RUNNING_EXPOSED,
            RunState.ABORTED_BEFORE_PREDICTION,
            RunState.INVALID,
        }
    ),
    RunState.RUNNING_EXPOSED: frozenset(
        {
            RunState.COMPLETED_RAW,
            RunState.PARTIAL_AFTER_PREDICTION_EXPOSURE,
            RunState.INVALID,
        }
    ),
    RunState.COMPLETED_RAW: frozenset({RunState.SEALED_RAW, RunState.INVALID}),
    RunState.SEALED_RAW: frozenset({RunState.SCORING, RunState.INVALID}),
    RunState.SCORING: frozenset({RunState.COMPLETE, RunState.INVALID}),
    RunState.COMPLETE: frozenset(),
    RunState.PARTIAL_AFTER_PREDICTION_EXPOSURE: frozenset(),
    RunState.ABORTED_BEFORE_PREDICTION: frozenset(),
    RunState.INVALID: frozenset(),
}


class InvalidTransition(RuntimeError):
    """Raised before any state mutation when a transition is not registered."""


class ManifestMismatch(RuntimeError):
    """Raised when immutable run inputs no longer match their frozen bindings."""


def canonical_json(value: object) -> bytes:
    """Return the frozen RFC-8259-compatible serialization used by run metadata."""
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class RunManifest:
    """Label-free immutable inputs for one sequential canonical execution."""

    experiment_id: str
    protocol_id: str
    corpus_id: str
    split: str
    run_id: str
    production_component: str
    exposure_ledger_path: str
    runtime_package_path: str
    runtime_package_checksum: str
    runtime_scenarios_path: str
    runtime_scenarios_checksum: str
    corpus_manifest_path: str
    corpus_manifest_checksum: str
    implementation_sha: str
    implementation_artifacts: tuple[tuple[str, str], ...]
    policy_version: str
    authorization_spec_version: str
    task_contract_schema_version: str
    runner_version: str
    runner_sha: str
    raw_schema_version: str
    ledger_version: str
    scenario_count: int
    scenario_order: tuple[str, ...]
    scenario_input_digests: tuple[tuple[str, str], ...]
    ordering_policy: str = "FROZEN_MANIFEST_ORDER"
    concurrency_policy: str = "SEQUENTIAL"
    manifest_id: str = RUN_MANIFEST_ID
    start_state: str = RunState.CREATED.value
    environment: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        required = {
            "experiment_id": self.experiment_id,
            "protocol_id": self.protocol_id,
            "corpus_id": self.corpus_id,
            "split": self.split,
            "run_id": self.run_id,
            "production_component": self.production_component,
            "implementation_sha": self.implementation_sha,
            "runner_sha": self.runner_sha,
            "policy_version": self.policy_version,
            "authorization_spec_version": self.authorization_spec_version,
            "task_contract_schema_version": self.task_contract_schema_version,
        }
        missing = sorted(key for key, value in required.items() if not value)
        if missing:
            raise ValueError(f"Run manifest fields must not be empty: {missing}")
        if self.scenario_count != len(self.scenario_order):
            raise ValueError("scenario_count must equal the frozen scenario_order length")
        if len(set(self.scenario_order)) != len(self.scenario_order):
            raise ValueError("Canonical run scenario_order must not contain duplicates")
        digest_map = dict(self.scenario_input_digests)
        if tuple(digest_map) != self.scenario_order or any(
            len(digest) != 64
            or digest.lower() != digest
            or any(character not in "0123456789abcdef" for character in digest)
            for digest in digest_map.values()
        ):
            raise ValueError("scenario input digests must bind every frozen scenario in order")
        if self.concurrency_policy != "SEQUENTIAL":
            raise ValueError("AUTH-COVERAGE-002 runner supports SEQUENTIAL execution only")
        if self.ordering_policy != "FROZEN_MANIFEST_ORDER":
            raise ValueError("ordering_policy must be FROZEN_MANIFEST_ORDER")
        if self.manifest_id != RUN_MANIFEST_ID or self.start_state != RunState.CREATED.value:
            raise ValueError("run manifest identity/start state differs from frozen contract")
        if self.runner_version != "AUTH-COVERAGE-002-RUNNER@1":
            raise ValueError("runner version differs from frozen contract")
        if self.protocol_id != EXECUTION_PROTOCOL_ID:
            raise ValueError("protocol identity differs from the frozen execution protocol")
        if self.production_component != PRODUCTION_COMPONENT_ID:
            raise ValueError("production component differs from the frozen public interface")
        if self.raw_schema_version != "AUTH-COVERAGE-002-RAW-SCHEMA@1":
            raise ValueError("raw schema version differs from frozen contract")
        if self.ledger_version != "AUTH-COVERAGE-EXPOSURE-LEDGER@1":
            raise ValueError("ledger version differs from frozen contract")
        for name, digest, length in (
            ("implementation_sha", self.implementation_sha, 40),
            ("runner_sha", self.runner_sha, 64),
            ("runtime_package_checksum", self.runtime_package_checksum, 64),
            ("runtime_scenarios_checksum", self.runtime_scenarios_checksum, 64),
            ("corpus_manifest_checksum", self.corpus_manifest_checksum, 64),
        ):
            if len(digest) != length or any(
                character not in "0123456789abcdef" for character in digest
            ):
                raise ValueError(f"{name} must be a lowercase hexadecimal digest")
        try:
            ResearchSplit(self.split)
        except ValueError as error:
            raise ValueError("split must be DEV, VALIDATION, or HELD_OUT") from error
        prohibited = {"expected_decision", "label", "family", "pair", "difficulty", "oracle"}
        serialized_keys = {key.casefold() for key in asdict(self)}
        if serialized_keys & prohibited:
            raise ValueError("Labels and analysis metadata are prohibited from run manifests")
        allowed_environment = {
            "python_version",
            "platform",
            "implementation",
            "timezone",
            "locale",
        }
        environment = dict(self.environment)
        if len(environment) != len(self.environment) or not set(environment) <= allowed_environment:
            raise ValueError("run environment contains an unregistered field")
        prohibited_terms = (
            "expected_decision",
            "label",
            "family",
            "pair",
            "difficulty",
            "oracle",
        )
        if any(
            term in value.casefold()
            for value in environment.values()
            for term in prohibited_terms
        ):
            raise ValueError("run environment contains prohibited analysis metadata")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> RunManifest:
        converted = dict(value)
        converted["implementation_artifacts"] = tuple(
            (str(item[0]), str(item[1]))
            for item in converted.get("implementation_artifacts", ())
        )
        converted["scenario_order"] = tuple(converted.get("scenario_order", ()))
        converted["scenario_input_digests"] = tuple(
            (str(item[0]), str(item[1]))
            for item in converted.get("scenario_input_digests", ())
        )
        converted["environment"] = tuple(
            (str(item[0]), str(item[1])) for item in converted.get("environment", ())
        )
        return cls(**converted)

    @property
    def digest(self) -> str:
        return sha256_bytes(canonical_json(self.as_dict()))

    def verify_bound_files(self, *, implementation_sha: str) -> None:
        if implementation_sha != self.implementation_sha:
            raise ManifestMismatch("production implementation SHA changed after run creation")
        checks = (
            (Path(self.runtime_package_path), self.runtime_package_checksum, "runtime package"),
            (
                Path(self.runtime_scenarios_path),
                self.runtime_scenarios_checksum,
                "runtime scenarios",
            ),
            (Path(self.corpus_manifest_path), self.corpus_manifest_checksum, "corpus manifest"),
            *(
                (Path(path), expected, f"implementation artifact {path}")
                for path, expected in self.implementation_artifacts
            ),
        )
        for path, expected, name in checks:
            if not path.is_file() or sha256_file(path) != expected:
                raise ManifestMismatch(f"{name} checksum does not match the run manifest")
        runtime_root = Path(self.runtime_package_path).resolve().parent
        try:
            Path(self.corpus_manifest_path).resolve().relative_to(runtime_root)
            Path(self.runtime_scenarios_path).resolve().relative_to(runtime_root)
        except ValueError as error:
            raise ManifestMismatch(
                "corpus manifest and scenarios must be inside runtime-only package"
            ) from error
        for path, name in (
            (Path(self.runtime_package_path), "runtime package"),
            (Path(self.corpus_manifest_path), "corpus manifest"),
        ):
            try:
                package = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise ManifestMismatch(f"{name} is not a valid binding manifest") from error
            expected_binding = {
                "corpus_id": self.corpus_id,
                "split": self.split,
                "scenario_ids": list(self.scenario_order),
                "scenario_input_digests": dict(self.scenario_input_digests),
                "runtime_scenarios_checksum": self.runtime_scenarios_checksum,
            }
            if (
                not isinstance(package, dict)
                or set(package) != set(expected_binding)
                or any(package.get(key) != value for key, value in expected_binding.items())
            ):
                raise ManifestMismatch(f"{name} split/corpus/order binding does not match")


@dataclass(frozen=True, slots=True)
class StateSnapshot:
    state_machine_id: str
    run_manifest_digest: str
    state: RunState
    transition_sequence: int
    first_prediction_observed: bool
    last_scenario_id: str | None = None
    reason: str | None = None


def _directory_fsync(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _durable_replace(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _directory_fsync(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


@contextmanager
def exclusive_run_lock(state_path: Path) -> Iterator[None]:
    """Serialize runner, sealer, and reconciler mutations for one run."""
    lock_path = state_path.with_name(f"{state_path.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


class RunStateStore:
    """Durable snapshot store with mechanically enforced terminal states."""

    def __init__(self, path: Path, manifest: RunManifest) -> None:
        self.path = path
        self.manifest = manifest

    def create(self) -> StateSnapshot:
        if self.path.exists():
            raise FileExistsError(self.path)
        snapshot = StateSnapshot(
            state_machine_id=STATE_MACHINE_ID,
            run_manifest_digest=self.manifest.digest,
            state=RunState.CREATED,
            transition_sequence=0,
            first_prediction_observed=False,
        )
        self._write(snapshot)
        return snapshot

    def load(self) -> StateSnapshot:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        expected_fields = {field.name for field in fields(StateSnapshot)}
        if not isinstance(raw, dict) or set(raw) != expected_fields:
            raise ValueError("run state has missing or unknown fields")
        if (
            not isinstance(raw["state_machine_id"], str)
            or not isinstance(raw["run_manifest_digest"], str)
            or not isinstance(raw["state"], str)
            or not isinstance(raw["transition_sequence"], int)
            or isinstance(raw["transition_sequence"], bool)
            or raw["transition_sequence"] < 0
            or not isinstance(raw["first_prediction_observed"], bool)
            or raw["last_scenario_id"] is not None
            and not isinstance(raw["last_scenario_id"], str)
            or raw["reason"] is not None
            and not isinstance(raw["reason"], str)
        ):
            raise ValueError("run state contains invalid field types")
        snapshot = StateSnapshot(
            state_machine_id=raw["state_machine_id"],
            run_manifest_digest=raw["run_manifest_digest"],
            state=RunState(raw["state"]),
            transition_sequence=raw["transition_sequence"],
            first_prediction_observed=raw["first_prediction_observed"],
            last_scenario_id=raw.get("last_scenario_id"),
            reason=raw.get("reason"),
        )
        if snapshot.state_machine_id != STATE_MACHINE_ID:
            raise ValueError("unknown run-state-machine identity")
        if snapshot.run_manifest_digest != self.manifest.digest:
            raise ManifestMismatch("run state is bound to a different manifest")
        if (
            snapshot.last_scenario_id is not None
            and snapshot.last_scenario_id not in self.manifest.scenario_order
        ):
            raise ValueError("run state scenario is outside the frozen manifest")
        return snapshot

    def transition(
        self,
        target: RunState,
        *,
        scenario_id: str | None = None,
        reason: str | None = None,
    ) -> StateSnapshot:
        current = self.load()
        if target not in LEGAL_TRANSITIONS[current.state]:
            raise InvalidTransition(f"illegal run transition: {current.state} -> {target}")
        prediction_observed = current.first_prediction_observed or target in {
            RunState.RUNNING_EXPOSED,
            RunState.PARTIAL_AFTER_PREDICTION_EXPOSURE,
        }
        updated = replace(
            current,
            state=target,
            transition_sequence=current.transition_sequence + 1,
            first_prediction_observed=prediction_observed,
            last_scenario_id=scenario_id or current.last_scenario_id,
            reason=reason,
        )
        self._write(updated)
        return updated

    def mark_call_boundary(self, scenario_id: str) -> StateSnapshot:
        """Durably cross the first-prediction boundary before invoking production."""
        current = self.load()
        if current.state is RunState.RUNNING_UNEXPOSED:
            return self.transition(RunState.RUNNING_EXPOSED, scenario_id=scenario_id)
        if current.state is not RunState.RUNNING_EXPOSED:
            raise InvalidTransition(f"production call forbidden while run is {current.state}")
        return current

    def mark_partial(self, scenario_id: str, reason: str) -> StateSnapshot:
        current = self.load()
        if not current.first_prediction_observed:
            raise InvalidTransition("partial-after-exposure requires a crossed call boundary")
        return self.transition(
            RunState.PARTIAL_AFTER_PREDICTION_EXPOSURE,
            scenario_id=scenario_id,
            reason=reason,
        )

    def require_scoring_allowed(self) -> None:
        if self.load().state is not RunState.SEALED_RAW:
            raise InvalidTransition("scoring requires SEALED_RAW")

    def require_prediction_allowed(self) -> None:
        if self.load().state not in {
            RunState.RUNNING_UNEXPOSED,
            RunState.RUNNING_EXPOSED,
        }:
            raise InvalidTransition("additional production predictions are forbidden")

    def _write(self, snapshot: StateSnapshot) -> None:
        payload = asdict(snapshot)
        payload["state"] = snapshot.state.value
        _durable_replace(self.path, canonical_json(payload) + b"\n")
