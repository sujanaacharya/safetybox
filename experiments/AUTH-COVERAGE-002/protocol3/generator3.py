#!/usr/bin/env python3
"""Crash-safe materialization governance for AUTH-COVERAGE-002-GENERATOR@3.

Benchmark semantics are delegated byte-for-byte to frozen Generator@2.  This
module adds only Protocol@3 governance.  It is a cooperative scientific
integrity boundary, not protection against an administrator who can rewrite
the verifier and every governance artifact together.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROTOCOL_ID = "AUTH-COVERAGE-002-PROTOCOL@3"
GENERATOR_ID = "AUTH-COVERAGE-002-GENERATOR@3"
REAL_ATTEMPT_ID = "AUTH-COVERAGE-002-CORPUS@3-ATTEMPT-1"
GENERATOR_IDENTITY_CHECKSUM = "e792195d841a664137bc4c31bcfb83be0be421fe394c029d9c4feee96b953a94"
GENERATOR2_SHA256 = "36b6ef0b0887b10627053087fdf156b62bdf4ff8caddd7798d1d2d8b1012b0a5"
REAL_STATE_ROOT = HERE / "materialization_state"
SPLITS = frozenset({"DEV", "VALIDATION", "HELD_OUT"})
ORDERING_POLICY = "GENERATOR2_SEEDED_SHUFFLE_PRESERVED"
RUNTIME_ID_POLICY = "OS_CSPRNG_AT_RUNTIME_BINDING;ABSENT_FROM_SEMANTIC_PACKAGE"
ZERO_HASH = "0" * 64


class GovernanceError(RuntimeError):
    """A fail-closed governance rejection."""


class CrashInjected(BaseException):
    """Test-only process-death surrogate; intentionally bypasses Exception handlers."""


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


authority = _load_module("auth_coverage_002_generator3_authority", HERE / "authority.py")
generator2 = _load_module(
    "auth_coverage_002_frozen_generator2", HERE.parent / "protocol2" / "generator2.py"
)


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _file_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("wb") as stream:
        stream.write(_canonical_json(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    _fsync_directory(path.parent)


def disposable_dev(
    seed: int, count: int = 800, *, template_root_offset: int = 0
) -> list[dict[str, Any]]:
    """Generate explicitly disposable DEV semantics through frozen Generator@2."""
    return generator2.generate_dev(seed, count, template_root_offset=template_root_offset)


def _registered_seed(verified: Any) -> int:
    """Derive the frozen seed from the provisioned commitment, never caller input."""
    material = (
        f"{verified.protocol_id}:{verified.generator_id}:{verified.corpus_attempt_id}:"
        f"{verified.split}:{verified.semantic_seed_or_entropy_commitment}"
    )
    return int(hashlib.sha256(material.encode()).hexdigest()[:16], 16)


def _event_hash(unsigned: dict[str, Any]) -> str:
    return _digest(unsigned)


class MaterializationStore:
    """Durable ledger, anchor, state, package, and manifest for one attempt."""

    def __init__(self, root: Path, attempt_id: str, *, synthetic: bool = False):
        resolved = root.resolve()
        if attempt_id == REAL_ATTEMPT_ID:
            if synthetic:
                raise GovernanceError("synthetic store cannot target the real corpus attempt")
            if resolved != REAL_STATE_ROOT.resolve():
                raise GovernanceError("real corpus attempt has a fixed governance-state root")
        elif not synthetic or "SYNTHETIC" not in attempt_id:
            raise GovernanceError("non-real stores require an explicit synthetic namespace")
        self.root = resolved
        self.attempt_id = attempt_id
        self.synthetic = synthetic

    def split_dir(self, split: str) -> Path:
        if split not in SPLITS:
            raise GovernanceError("unsupported canonical split")
        return self.root / self.attempt_id / split

    def path(self, split: str, name: str) -> Path:
        return self.split_dir(split) / name

    def _read_events(self, split: str) -> list[dict[str, Any]]:
        ledger = self.path(split, "materialization-ledger.jsonl")
        events: list[dict[str, Any]] = []
        previous = ZERO_HASH
        try:
            lines = ledger.read_bytes().splitlines()
        except OSError as exc:
            raise GovernanceError("ledger unavailable") from exc
        if not lines:
            raise GovernanceError("empty ledger")
        for index, line in enumerate(lines, 1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise GovernanceError("ledger corrupt") from exc
            if not isinstance(event, dict):
                raise GovernanceError("ledger event is not an object")
            recorded_hash = event.get("event_hash")
            unsigned = dict(event)
            unsigned.pop("event_hash", None)
            if (
                unsigned.get("sequence") != index
                or unsigned.get("previous_hash") != previous
                or recorded_hash != _event_hash(unsigned)
                or unsigned.get("attempt") != self.attempt_id
                or unsigned.get("split") != split
            ):
                raise GovernanceError("ledger chain invalid")
            previous = str(recorded_hash)
            events.append(event)
        return events

    def _append(self, split: str, event_type: str, authority_digest: str) -> dict[str, Any]:
        directory = self.split_dir(split)
        directory.mkdir(parents=True, exist_ok=True)
        ledger = self.path(split, "materialization-ledger.jsonl")
        if ledger.exists():
            events = self._read_events(split)
            previous = events[-1]["event_hash"]
            sequence = len(events) + 1
        else:
            previous = ZERO_HASH
            sequence = 1
        unsigned = {
            "sequence": sequence,
            "previous_hash": previous,
            "event": event_type,
            "protocol_id": PROTOCOL_ID,
            "generator_id": GENERATOR_ID,
            "attempt": self.attempt_id,
            "split": split,
            "authority_artifact_digest": authority_digest,
        }
        event = {**unsigned, "event_hash": _event_hash(unsigned)}
        with ledger.open("ab") as stream:
            stream.write(_canonical_json(event) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        _fsync_directory(directory)
        anchor = {
            "schema": "AUTH-COVERAGE-002-MATERIALIZATION-ANCHOR@1",
            "attempt": self.attempt_id,
            "split": split,
            "ledger_count": sequence,
            "ledger_head": event["event_hash"],
        }
        _atomic_json(self.path(split, "ledger-anchor.json"), anchor)
        state = {
            "schema": "AUTH-COVERAGE-002-MATERIALIZATION-STATE@1",
            "attempt": self.attempt_id,
            "split": split,
            "authority_artifact_digest": authority_digest,
            "state": event_type,
            "ledger_count": sequence,
            "ledger_head": event["event_hash"],
        }
        _atomic_json(self.path(split, "state.json"), state)
        return event

    def _package_observation(self, split: str) -> tuple[int, bool]:
        package = self.path(split, "semantic-records.jsonl")
        if not package.exists():
            return 0, False
        count = 0
        malformed = False
        for line in package.read_bytes().splitlines():
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                malformed = True
                continue
            if isinstance(value, dict):
                count += 1
            else:
                malformed = True
        return count, malformed

    def bind_authority(self, verified: Any) -> None:
        """Persist the exact verified binding used by independent manifest checks."""
        path = self.path(verified.split, "authority-binding.json")
        value = {
            key: value
            for key, value in vars(verified).items()
            if key != "_load_proof"
        }
        if path.exists():
            if self._load_json(path) != value:
                raise GovernanceError("authority binding changed across retry")
            return
        _atomic_json(path, value)

    def _load_json(self, path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise GovernanceError(f"invalid governance artifact: {path.name}") from exc
        if not isinstance(value, dict):
            raise GovernanceError(f"invalid governance artifact: {path.name}")
        return value

    def _integrity(self, split: str) -> tuple[list[dict[str, Any]], str | None]:
        directory = self.split_dir(split)
        ledger = self.path(split, "materialization-ledger.jsonl")
        anchor_path = self.path(split, "ledger-anchor.json")
        state_path = self.path(split, "state.json")
        if not ledger.exists():
            if directory.exists() and any(directory.iterdir()):
                return [], "LEDGER_MISSING"
            return [], None
        try:
            events = self._read_events(split)
        except GovernanceError:
            return [], "LEDGER_CORRUPT"
        if not anchor_path.exists():
            return events, "ANCHOR_MISMATCH"
        try:
            anchor = self._load_json(anchor_path)
        except GovernanceError:
            return events, "ANCHOR_MISMATCH"
        if (
            anchor.get("ledger_count") != len(events)
            or anchor.get("ledger_head") != events[-1]["event_hash"]
            or anchor.get("attempt") != self.attempt_id
            or anchor.get("split") != split
        ):
            return events, "ANCHOR_MISMATCH"
        if not state_path.exists():
            return events, "STATE_INCONSISTENT"
        try:
            state = self._load_json(state_path)
        except GovernanceError:
            return events, "STATE_INCONSISTENT"
        if (
            state.get("ledger_count") != len(events)
            or state.get("ledger_head") != events[-1]["event_hash"]
            or state.get("state") != events[-1]["event"]
            or state.get("authority_artifact_digest")
            != events[-1]["authority_artifact_digest"]
        ):
            return events, "STATE_INCONSISTENT"
        return events, None

    def reconcile(self, split: str) -> str:
        """Classify durable evidence and fail closed; never creates semantic data."""
        events, problem = self._integrity(split)
        if problem:
            return problem
        if not events:
            return "NOT_STARTED"
        kinds = [str(event["event"]) for event in events]
        authority_digest = str(events[-1]["authority_artifact_digest"])
        record_count, malformed = self._package_observation(split)
        if "SEALED" in kinds:
            if kinds[-1] != "SEALED":
                return "STATE_INCONSISTENT"
            manifest = self.path(split, "manifest.json")
            if not manifest.exists():
                return "MANIFEST_MISMATCH"
            try:
                verify_manifest(manifest, self, split)
            except GovernanceError:
                return "MANIFEST_MISMATCH"
            return "SEALED"
        if "PARTIAL_BLOCKED" in kinds:
            return "PARTIAL_OBSERVED_BLOCKED"
        if "COMPLETED" in kinds:
            manifest = self.path(split, "manifest.json")
            if manifest.exists():
                try:
                    verify_manifest(manifest, self, split)
                except GovernanceError:
                    return "MANIFEST_MISMATCH"
            return "COMPLETED_UNSEALED"
        observed = record_count > 0 or "FIRST_RECORD_DURABLE" in kinds
        if observed:
            if "FIRST_RECORD_DURABLE" not in kinds:
                self._append(split, "FIRST_RECORD_DURABLE", authority_digest)
            self._append(split, "PARTIAL_BLOCKED", authority_digest)
            return "PARTIAL_OBSERVED_BLOCKED"
        if malformed:
            return "STARTED_UNOBSERVED"
        return "STARTED_UNOBSERVED"

    def sealed_digest(self, split: str) -> str:
        if self.reconcile(split) != "SEALED":
            raise GovernanceError(f"{split} is not sealed")
        return _file_digest(self.path(split, "manifest.json"))


def construct_manifest(
    verified: Any, store: MaterializationStore, records: list[dict[str, Any]]
) -> dict[str, Any]:
    events = store._read_events(verified.split)
    completed_index = next(
        (index for index, event in enumerate(events) if event["event"] == "COMPLETED"), None
    )
    if completed_index is None:
        raise GovernanceError("manifest requires durable COMPLETED state")
    completed = events[completed_index]
    package = store.path(verified.split, "semantic-records.jsonl")
    return {
        "manifest_schema": "AUTH-COVERAGE-002-CANONICAL-MANIFEST@3",
        "protocol_id": verified.protocol_id,
        "protocol_checksum": verified.protocol_checksum,
        "generator_id": verified.generator_id,
        "generator_checksum": verified.generator_checksum,
        "corpus_attempt_id": verified.corpus_attempt_id,
        "split": verified.split,
        "authority_artifact_digest": verified.artifact_digest,
        "semantic_seed_or_entropy_commitment": verified.semantic_seed_or_entropy_commitment,
        "record_count": len(records),
        "semantic_package_digest": _file_digest(package),
        "ordering_policy": ORDERING_POLICY,
        "runtime_id_policy": RUNTIME_ID_POLICY,
        "source_sha": verified.semantic_source_sha256,
        "ledger_head": completed["event_hash"],
        "ledger_count": completed_index + 1,
        "terminal_state": "SEALED",
    }


def verify_manifest(path: Path, store: MaterializationStore, split: str) -> dict[str, Any]:
    """Independently verify every bound manifest field from durable evidence."""
    try:
        manifest = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise GovernanceError("manifest unavailable or malformed") from exc
    if not isinstance(manifest, dict):
        raise GovernanceError("manifest is not an object")
    events = store._read_events(split)
    completed_index = next(
        (index for index, event in enumerate(events) if event["event"] == "COMPLETED"), None
    )
    if completed_index is None:
        raise GovernanceError("manifest has no completed ledger binding")
    completed = events[completed_index]
    binding = store._load_json(store.path(split, "authority-binding.json"))
    unsigned_binding = dict(binding)
    recorded_binding_digest = unsigned_binding.pop("artifact_digest", None)
    if recorded_binding_digest != _digest(unsigned_binding):
        raise GovernanceError("authority binding artifact digest mismatch")
    if binding.get("artifact_digest") != completed["authority_artifact_digest"]:
        raise GovernanceError("authority binding/ledger mismatch")
    if not store.synthetic and authority.REAL_ARTIFACT_DIGESTS.get(split) != binding.get(
        "artifact_digest"
    ):
        raise GovernanceError("real authority binding is not protocol provisioned")
    package = store.path(split, "semantic-records.jsonl")
    count, malformed = store._package_observation(split)
    expected = {
        "manifest_schema": "AUTH-COVERAGE-002-CANONICAL-MANIFEST@3",
        "protocol_id": binding.get("protocol_id"),
        "protocol_checksum": binding.get("protocol_checksum"),
        "generator_id": binding.get("generator_id"),
        "generator_checksum": binding.get("generator_checksum"),
        "corpus_attempt_id": store.attempt_id,
        "split": split,
        "authority_artifact_digest": completed["authority_artifact_digest"],
        "record_count": count,
        "semantic_package_digest": _file_digest(package) if package.exists() else None,
        "ordering_policy": ORDERING_POLICY,
        "runtime_id_policy": RUNTIME_ID_POLICY,
        "source_sha": binding.get("semantic_source_sha256"),
        "ledger_head": completed["event_hash"],
        "ledger_count": completed_index + 1,
        "terminal_state": "SEALED",
    }
    if malformed or set(manifest) != set(expected) | {"semantic_seed_or_entropy_commitment"}:
        raise GovernanceError("manifest shape mismatch")
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise GovernanceError("manifest binding mismatch")
    commitment = manifest.get("semantic_seed_or_entropy_commitment")
    if commitment != binding.get("semantic_seed_or_entropy_commitment"):
        raise GovernanceError("manifest commitment mismatch")
    return manifest


def _write_record(stream: Any, record: dict[str, Any]) -> None:
    stream.write(_canonical_json(record) + b"\n")
    stream.flush()
    os.fsync(stream.fileno())


class CanonicalMaterializer:
    """Canonical-only materializer.  It has no split, seed, or downgrade input."""

    def __init__(self, verifier: Any, store: MaterializationStore):
        if type(verifier) is not authority.AuthorityVerifier:
            raise GovernanceError("materialization requires the built-in authority verifier")
        if type(store) is not MaterializationStore:
            raise GovernanceError("materialization requires the built-in durable store")
        self.verifier = verifier
        self.store = store
        self._store_identity = (store.root, store.attempt_id, store.synthetic)
        self._assert_builtin_boundary()

    def _assert_builtin_boundary(self) -> None:
        verifier_fields = {
            "attempt_id",
            "protocol_id",
            "generator_id",
            "approved_digests",
            "authority_root",
            "synthetic",
            "_loaded_ids",
        }
        if set(vars(self.verifier)) != verifier_fields:
            raise GovernanceError("authority verifier instance was modified")
        if set(vars(self.store)) != {"root", "attempt_id", "synthetic"}:
            raise GovernanceError("durable store instance was modified")
        if (self.store.root, self.store.attempt_id, self.store.synthetic) != self._store_identity:
            raise GovernanceError("durable store identity changed after construction")
        real_domain = (
            self.store.attempt_id == REAL_ATTEMPT_ID
            or self.verifier.attempt_id == REAL_ATTEMPT_ID
        )
        if real_domain:
            if (
                self.store.root != REAL_STATE_ROOT.resolve()
                or self.store.attempt_id != REAL_ATTEMPT_ID
                or self.store.synthetic
                or self.verifier.attempt_id != REAL_ATTEMPT_ID
                or self.verifier.synthetic
                or self.verifier.authority_root != authority.AUTHORITY_ROOT.resolve()
                or self.verifier.approved_digests != authority.REAL_ARTIFACT_DIGESTS
            ):
                raise GovernanceError("real materialization boundary was modified")

    def materialize(self, verified: Any, *, crash_at: str | None = None) -> dict[str, Any]:
        self._assert_builtin_boundary()
        self.verifier.assert_loaded(verified)
        if verified.corpus_attempt_id != self.store.attempt_id:
            raise GovernanceError("authority/store attempt mismatch")
        if bool(self.verifier.synthetic) != bool(self.store.synthetic):
            raise GovernanceError("authority/store trust domain mismatch")
        state = self.store.reconcile(verified.split)
        if state not in {"NOT_STARTED", "STARTED_UNOBSERVED"}:
            raise GovernanceError(f"canonical authority is unavailable: {state}")
        directory = self.store.split_dir(verified.split)
        directory.mkdir(parents=True, exist_ok=True)
        if state == "NOT_STARTED":
            self.store.bind_authority(verified)
            self.store._append(verified.split, "AUTHORITY_CONSUMED", verified.artifact_digest)
            if crash_at == "after_authority_consumption":
                raise CrashInjected(crash_at)
            self.store._append(verified.split, "STARTED", verified.artifact_digest)
        elif not any(
            event["event"] == "STARTED" for event in self.store._read_events(verified.split)
        ):
            # Complete interrupted durable ordering without consuming again.
            self.store._append(verified.split, "STARTED", verified.artifact_digest)
        if crash_at == "after_started":
            raise CrashInjected(crash_at)
        if crash_at == "before_first_write":
            raise CrashInjected(crash_at)

        # Semantic generation happens only after all authority/state rejection paths.
        seed = _registered_seed(verified)
        records = generator2.generate_authoring(seed, verified.split, verified.record_count)
        package = self.store.path(verified.split, "semantic-records.jsonl")
        # A pre-observation retry reuses authority and deterministically replaces debris.
        mode = "wb"
        with package.open(mode) as stream:
            if crash_at == "during_first_write":
                stream.write(_canonical_json(records[0])[:17])
                stream.flush()
                os.fsync(stream.fileno())
                raise CrashInjected(crash_at)
            for index, record in enumerate(records):
                _write_record(stream, record)
                if index == 0:
                    if crash_at == "after_first_fsync":
                        raise CrashInjected(crash_at)
                    self.store._append(
                        verified.split, "FIRST_RECORD_DURABLE", verified.artifact_digest
                    )
                    if crash_at == "after_observation_boundary_event":
                        raise CrashInjected(crash_at)
                if crash_at == "mid_generation" and index == max(1, len(records) // 2):
                    raise CrashInjected(crash_at)
        _fsync_directory(directory)
        if crash_at == "after_last_record":
            raise CrashInjected(crash_at)
        if crash_at == "before_completed":
            raise CrashInjected(crash_at)
        self.store._append(verified.split, "COMPLETED", verified.artifact_digest)
        if crash_at == "after_completed":
            raise CrashInjected(crash_at)
        if crash_at == "before_manifest":
            raise CrashInjected(crash_at)
        manifest = construct_manifest(verified, self.store, records)
        manifest_path = self.store.path(verified.split, "manifest.json")
        _atomic_json(manifest_path, manifest)
        if crash_at == "after_manifest":
            raise CrashInjected(crash_at)
        if crash_at == "during_manifest_verification":
            raise CrashInjected(crash_at)
        verify_manifest(manifest_path, self.store, verified.split)
        if crash_at == "before_sealed":
            raise CrashInjected(crash_at)
        self.store._append(verified.split, "SEALED", verified.artifact_digest)
        if crash_at == "after_sealed":
            raise CrashInjected(crash_at)
        return manifest


def canonical_materialize(
    artifact_path: Path,
    store: MaterializationStore,
    *,
    verifier: Any | None = None,
    gate_a_path: Path | None = None,
    crash_at: str | None = None,
) -> dict[str, Any]:
    """Verify a provisioned artifact, then execute its immutable materialization request."""
    if crash_at == "before_authority_verification":
        raise CrashInjected(crash_at)
    if type(store) is not MaterializationStore:
        raise GovernanceError("canonical entry point requires the built-in durable store")
    if store.attempt_id == REAL_ATTEMPT_ID and verifier is not None:
        raise GovernanceError("real materialization does not accept an injected verifier")
    selected = verifier or authority.AuthorityVerifier()
    verified = selected.load(artifact_path, gate_a_path=gate_a_path, store=store)
    if crash_at == "after_authority_verification":
        raise CrashInjected(crash_at)
    return CanonicalMaterializer(selected, store).materialize(verified, crash_at=crash_at)


def gate_b_authorizes_materialization(_gate_b: object) -> bool:
    """Gate B is deliberately incapable of granting materialization authority."""
    return False


def gate_a_authorizes_production(_gate_a: object) -> bool:
    """Gate A is deliberately incapable of granting production authority."""
    return False


def _cli(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generator@3 governance verifier")
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify = subparsers.add_parser("verify-authority")
    verify.add_argument("split", choices=sorted(SPLITS))
    disposable = subparsers.add_parser("disposable-dev")
    disposable.add_argument("--seed", type=int, required=True)
    disposable.add_argument("--count", type=int, default=800)
    arguments = parser.parse_args(list(argv) if argv is not None else None)
    if arguments.command == "verify-authority":
        # Verification only: the CLI intentionally exposes no canonical write command.
        authority.AuthorityVerifier().load(authority.authority_path(arguments.split))
        return 0
    records = disposable_dev(arguments.seed, arguments.count)
    print(_digest(records))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
